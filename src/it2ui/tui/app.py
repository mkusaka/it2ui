from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

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
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #search_row { height: auto; }
    #search_label { color: $text-muted; }
    #search { width: 1fr; height: 3; }
    #search_help { color: $text-muted; height: 3; content-align: right middle; }
    #status { height: auto; }
    Input { border: round $surface; }
    Input:focus { border: round $accent; }
    """

    def __init__(self, *, backend: Backend, initial_snapshot: Snapshot) -> None:
        super().__init__()
        self.controller = ItwmController(backend=backend, initial_snapshot=initial_snapshot)
        self._row_index: list[_TableRow] = []
        self._last_ctrl_q_at: Optional[float] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="body"):
            with Horizontal(id="search_row"):
                yield Static("Search:", id="search_label")
                yield Input(placeholder="Type to filter (fuzzy).", id="search")
                yield Static(
                    "Esc: clear • ↑↓: select • Enter: activate • Ctrl+Q: quit", id="search_help"
                )
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
        query = self.controller.state.query.strip()
        query_part = f'Query: "{query}"' if query else "Query: (empty)"
        hint = " Enter: activate  Up/Down: select  Ctrl+HJKL: pane  Ctrl+Q: quit"
        status = self.controller.state.status.strip()
        status_part = f" | {status}" if status else ""
        self.query_one("#status", Static).update(f"{query_part}{status_part}{hint}")

    async def on_key(self, event: events.Key) -> None:
        # Double-press Ctrl+Q to quit (to avoid accidental exits).
        if event.key == "ctrl+q":
            now = time.monotonic()
            if self._last_ctrl_q_at is not None and (now - self._last_ctrl_q_at) <= 0.75:
                self.exit()
            else:
                self._last_ctrl_q_at = now
                self._status("Press Ctrl+Q again to quit")
            event.stop()
            return

        self._last_ctrl_q_at = None

        if event.key == "escape":
            search = self.query_one("#search", Input)
            search.value = ""
            self.controller.set_query("")
            self._render()
            event.stop()
            return

        if event.key in ("up", "down"):
            delta = -1 if event.key == "up" else 1
            self.controller.select_index(self.controller.state.selected_index + delta)
            self._render()
            event.stop()
            return

        if event.key == "enter":
            await self._activate_selected()
            event.stop()
            return

        if event.key in ("ctrl+h", "ctrl+j", "ctrl+k", "ctrl+l"):
            mapping = {
                "ctrl+h": PaneDirection.LEFT,
                "ctrl+j": PaneDirection.DOWN,
                "ctrl+k": PaneDirection.UP,
                "ctrl+l": PaneDirection.RIGHT,
            }
            await self.controller.move_pane(mapping[event.key])
            self._render()
            event.stop()
            return

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.controller.select_index(self._table().cursor_row)
        self._render_status()

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search":
            return
        self.controller.set_query(event.value)
        self._render()

    async def _activate_selected(self) -> None:
        try:
            await self.controller.activate_selected()
            self._render()
        except Exception as e:
            self._status(str(e))
