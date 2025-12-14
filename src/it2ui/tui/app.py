import time
from dataclasses import dataclass
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Input, Static

from it2ui.backend.protocol import Backend, PaneDirection
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
        ("ctrl+h", "pane_left", "Pane←"),
        ("ctrl+j", "pane_down", "Pane↓"),
        ("ctrl+k", "pane_up", "Pane↑"),
        ("ctrl+l", "pane_right", "Pane→"),
        ("ctrl+q", "quit_maybe", "Quit"),
    ]

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
        self.controller = ItwmController(backend=backend, initial_snapshot=initial_snapshot)
        self._row_index: list[_TableRow] = []
        self._last_ctrl_q_at: float | None = None

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
        table.add_columns("*", "Win", "Tab", "Session", "Name")
        self.query_one("#search", Input).focus()
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
                f"{row.window_index}:{row.window_id}",
                f"{row.tab_index}:{row.tab_id}",
                row.session_id,
                row.display_name,
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
        if self._last_ctrl_q_at is not None and (now - self._last_ctrl_q_at) <= 0.75:
            self.exit()
            return
        self._last_ctrl_q_at = now
        self.notify("Press Ctrl+Q again to quit", timeout=0.75)

    async def action_quit(self) -> None:
        # Override Textual's default quit action to require a double-press.
        self.action_quit_maybe()

    async def on_key(self, event: events.Key) -> None:
        if event.key != "ctrl+q":
            self._last_ctrl_q_at = None

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

    async def _pane(self, direction: PaneDirection) -> None:
        await self.controller.move_pane(direction)
        self._render()

    async def action_pane_left(self) -> None:
        await self._pane(PaneDirection.LEFT)

    async def action_pane_down(self) -> None:
        await self._pane(PaneDirection.DOWN)

    async def action_pane_up(self) -> None:
        await self._pane(PaneDirection.UP)

    async def action_pane_right(self) -> None:
        await self._pane(PaneDirection.RIGHT)

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
            await self.controller.activate_selected()
            self._render()
        except Exception as e:
            self._status(str(e))
