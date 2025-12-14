from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from it2ui.backend.protocol import Backend
from it2ui.domain.models import SessionRow, Snapshot, rows_from_snapshot
from it2ui.domain.search import filter_and_rank


@dataclass
class ItwmState:
    all_rows: list[SessionRow]
    filtered_rows: list[SessionRow]
    query: str = ""
    selected_index: int = 0
    status: str = ""

    def clamp_selection(self) -> None:
        if not self.filtered_rows:
            self.selected_index = 0
            return
        self.selected_index = max(0, min(self.selected_index, len(self.filtered_rows) - 1))


class ItwmController:
    def __init__(self, backend: Backend, initial_snapshot: Snapshot) -> None:
        rows = rows_from_snapshot(initial_snapshot)
        self.backend = backend
        self.state = ItwmState(all_rows=rows, filtered_rows=list(rows))
        self._select_active_if_present()

    def set_query(self, query: str) -> None:
        self.state.query = query
        self.state.filtered_rows = filter_and_rank(self.state.all_rows, query)
        self.state.clamp_selection()
        self._select_active_if_present()

    def set_rows_from_snapshot(self, snapshot: Snapshot) -> None:
        self.state.all_rows = rows_from_snapshot(snapshot)
        self.set_query(self.state.query)

    def selected_row(self) -> Optional[SessionRow]:
        if not self.state.filtered_rows:
            return None
        self.state.clamp_selection()
        return self.state.filtered_rows[self.state.selected_index]

    def select_index(self, index: int) -> None:
        self.state.selected_index = index
        self.state.clamp_selection()

    async def activate_selected(self) -> str | None:
        row = self.selected_row()
        if row is None:
            self.state.status = "No session selected"
            return None
        await self.backend.activate_session(row.session_id)
        self.state.status = ""
        return row.display_name

    def list_rows(self) -> Sequence[SessionRow]:
        return self.state.filtered_rows

    def _select_active_if_present(self) -> None:
        if not self.state.filtered_rows:
            return
        for i, row in enumerate(self.state.filtered_rows):
            if row.is_active:
                self.state.selected_index = i
                break
