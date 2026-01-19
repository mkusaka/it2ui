import asyncio
import time
from dataclasses import dataclass
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Input, Static

from it2ui.backend.protocol import Backend
from it2ui.domain.controller import ItwmController
from it2ui.domain.models import Snapshot


@dataclass(frozen=True)
class _TableRow:
    session_id: str


class It2uiApp(App[None]):
    BINDINGS = [
        ("escape", "clear_query", "Clear"),
        ("enter", "activate", "Activate"),
        ("up", "select_up", "Up"),
        ("down", "select_down", "Down"),
        ("ctrl+p", "select_up", "Up"),
        ("ctrl+n", "select_down", "Down"),
        ("ctrl+c", "quit_maybe", "Quit"),
    ]

    # Disable command palette to free up ctrl+p
    COMMAND_PALETTE_BINDING = "ctrl+shift+p"

    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #search_row { height: 3; }
    #search { width: 1fr; height: 3; }
    #status { height: auto; }
    Input { background: $panel; border: round $accent; color: $text; }
    Input:focus { border: round $accent; }
    """

    def __init__(self, *, backend: Backend, initial_snapshot: Snapshot) -> None:
        super().__init__()
        self.backend = backend
        self.controller = ItwmController(backend=backend, initial_snapshot=initial_snapshot)
        self._row_index: list[_TableRow] = []
        self._last_ctrl_c_at: float | None = None
        self._events_task: asyncio.Task[None] | None = None
        self._refresh_task: asyncio.Task[None] | None = None
        self._refresh_pending = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="body"):
            with Horizontal(id="search_row"):
                yield Input(placeholder="Type to filter (fuzzy).", id="search")
            yield DataTable(id="table")
            yield Static("", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        table: DataTable[str] = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("*", "Name", "Cwd", "Command")
        self.query_one("#search", Input).focus()
        self._render()
        self._events_task = asyncio.create_task(self._watch_backend_events())

    async def on_unmount(self) -> None:
        for task in (self._events_task, self._refresh_task):
            if task is not None:
                task.cancel()

    async def _watch_backend_events(self) -> None:
        try:
            async for _event in self.backend.events():
                self._request_refresh()
        except Exception as e:
            self._status(str(e))

    def _request_refresh(self) -> None:
        self._refresh_pending = True
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._debounced_refresh())

    async def _debounced_refresh(self) -> None:
        while self._refresh_pending:
            self._refresh_pending = False
            await asyncio.sleep(0.2)
            await self._refresh_snapshot()

    async def _refresh_snapshot(self) -> None:
        try:
            snapshot = await self.backend.snapshot()
        except Exception as e:
            self._status(str(e))
            return
        self.controller.set_rows_from_snapshot(snapshot)
        self._render()

    def _render(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=False)
        self._row_index = []

        rows = list(self.controller.list_rows())
        for row in rows:
            active = "▶" if row.is_active else ""
            table.add_row(
                active,
                row.display_name,
                row.display_cwd,
                row.command_line,
            )
            self._row_index.append(_TableRow(session_id=row.session_id))

        if rows:
            self.controller.state.clamp_selection()
            table.cursor_coordinate = Coordinate(self.controller.state.selected_index, 0)
        self._render_status()

    def _table(self) -> DataTable[Any]:
        return self.query_one("#table", DataTable)

    def _status(self, message: str) -> None:
        self.controller.state.status = message
        self._render_status()

    def _render_status(self) -> None:
        status = self.controller.state.status.strip()
        self.query_one("#status", Static).update(status)

    def action_quit_maybe(self) -> None:
        now = time.monotonic()
        if self._last_ctrl_c_at is not None and (now - self._last_ctrl_c_at) <= 0.75:
            self.exit()
            return
        self._last_ctrl_c_at = now
        self.notify("Press Ctrl+C again to quit", timeout=0.75)

    async def action_quit(self) -> None:
        # Override Textual's default quit action to require a double-press.
        self.action_quit_maybe()

    async def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if isinstance(focused, Input) and focused.id == "search":
            if event.key == "ctrl+h":
                focused.action_delete_left()
                event.stop()
                return
            # Ctrl+A: move to beginning of line (macOS/Emacs style)
            if event.key == "ctrl+a":
                focused.action_home()
                event.stop()
                return
            # Cmd+A: select all text in input (macOS style)
            if event.key == "cmd+a":
                focused.action_select_all()
                event.stop()
                return

        if event.key != "ctrl+c":
            self._last_ctrl_c_at = None

    def action_clear_query(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        self.controller.set_query("")
        self._status("")
        self._render()

    async def action_activate(self) -> None:
        await self._activate_selected()

    def action_select_up(self) -> None:
        self.controller.select_index(self.controller.state.selected_index - 1)
        self._render()

    def action_select_down(self) -> None:
        self.controller.select_index(self.controller.state.selected_index + 1)
        self._render()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.controller.select_index(self._table().cursor_row)
        self._render_status()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search":
            return
        self.controller.set_query(event.value)
        self.controller.select_index(0)
        self._status("")
        self._render()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search":
            return
        await self._activate_selected()

    async def _activate_selected(self) -> None:
        try:
            activated_name = await self.controller.activate_selected()
            if activated_name:
                self.notify(f"Focused: {activated_name}", timeout=0.75)
            self._render()
        except Exception as e:
            self._status(str(e))
