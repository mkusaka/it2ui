from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Input, Static

from itwm.backend.protocol import Backend, PaneDirection
from itwm.domain.controller import ItwmController
from itwm.domain.models import Snapshot


@dataclass(frozen=True)
class _TableRow:
    session_id: str


class ItwmApp(App[None]):
    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #search { height: auto; }
    #status { height: auto; }
    """

    def __init__(self, *, backend: Backend, initial_snapshot: Snapshot) -> None:
        super().__init__()
        self.controller = ItwmController(backend=backend, initial_snapshot=initial_snapshot)
        self._row_index: list[_TableRow] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="body"):
            with Horizontal():
                yield Static("Search:", id="search_label")
                yield Input(placeholder="type to filter (fuzzy)", id="search")
            yield DataTable(id="table")
            yield Static("", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        table: DataTable[str] = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("*", "Win", "Tab", "Session", "Name")
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
        self.query_one("#status", Static).update(self.controller.state.status)

    def _search_input(self) -> Input:
        return self.query_one("#search", Input)

    def _table(self) -> DataTable[Any]:
        return self.query_one("#table", DataTable)

    def _status(self, message: str) -> None:
        self.controller.state.status = message
        self.query_one("#status", Static).update(message)

    async def on_key(self, event: events.Key) -> None:
        search = self._search_input()
        table = self._table()

        if search.has_focus:
            if event.key == "escape":
                search.value = ""
                self.controller.set_query("")
                table.focus()
                self._render()
                event.stop()
            elif event.key == "enter":
                await self._activate_selected()
                event.stop()
            else:
                return
            return

        if event.key in ("/", "ctrl+f"):
            search.focus()
            search.action_select_all()
            event.stop()
            return

        if event.key == "q":
            self.exit()
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

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "search":
            return
        self.controller.set_query(event.value)
        self._render()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.controller.select_index(self._table().cursor_row)
        self.query_one("#status", Static).update(self.controller.state.status)

    async def _activate_selected(self) -> None:
        try:
            await self.controller.activate_selected()
            self._render()
        except Exception as e:
            self._status(str(e))
