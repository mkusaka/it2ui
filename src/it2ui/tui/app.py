from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Static

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
    #search_value { width: 1fr; }
    #search_value { color: $text; }
    #search_help { color: $text-muted; }
    #status { height: auto; }
    """

    def __init__(self, *, backend: Backend, initial_snapshot: Snapshot) -> None:
        super().__init__()
        self.controller = ItwmController(backend=backend, initial_snapshot=initial_snapshot)
        self._row_index: list[_TableRow] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="body"):
            with Horizontal(id="search_row"):
                yield Static("Search:", id="search_label")
                yield Static("", id="search_value")
                yield Static("Type to filter • Backspace: delete • Esc: clear • Ctrl+Q: quit", id="search_help")
            yield DataTable(id="table")
            yield Static("", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        table: DataTable[str] = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("*", "Win", "Tab", "Session", "Name")
        table.focus()
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
        self._render_search_value()

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

    def _render_search_value(self) -> None:
        query = self.controller.state.query.strip()
        self.query_one("#search_value", Static).update(query)

    async def on_key(self, event: events.Key) -> None:
        table = self._table()

        if event.key == "ctrl+q":
            self.exit()
            event.stop()
            return

        if event.key == "escape":
            self.controller.set_query("")
            self._render()
            event.stop()
            return

        if event.key == "backspace":
            q = self.controller.state.query
            if q:
                self.controller.set_query(q[:-1])
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

        if len(event.key) == 1 and event.key.isprintable():
            self.controller.set_query(self.controller.state.query + event.key)
            self._render()
            event.stop()
            return

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.controller.select_index(self._table().cursor_row)
        self._render_status()

    async def _activate_selected(self) -> None:
        try:
            await self.controller.activate_selected()
            self._render()
        except Exception as e:
            self._status(str(e))
