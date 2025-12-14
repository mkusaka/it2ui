from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class SessionRow:
    window_id: str
    window_index: int
    tab_id: str
    tab_index: int
    session_id: str
    name: str
    is_active: bool

    @property
    def display_name(self) -> str:
        return self.name or "(unnamed)"


@dataclass(frozen=True)
class TabSnapshot:
    tab_id: str
    tab_index: int
    sessions: Sequence["Snapshot.SessionSnapshot"]


@dataclass(frozen=True)
class WindowSnapshot:
    window_id: str
    window_index: int
    tabs: Sequence[TabSnapshot]


@dataclass(frozen=True)
class Snapshot:
    @dataclass(frozen=True)
    class SessionSnapshot:
        session_id: str
        name: str

    windows: Sequence[WindowSnapshot]
    active_session_id: Optional[str]


def rows_from_snapshot(snapshot: Snapshot) -> list[SessionRow]:
    rows: list[SessionRow] = []
    for window in snapshot.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                rows.append(
                    SessionRow(
                        window_id=window.window_id,
                        window_index=window.window_index,
                        tab_id=tab.tab_id,
                        tab_index=tab.tab_index,
                        session_id=session.session_id,
                        name=session.name,
                        is_active=(snapshot.active_session_id == session.session_id),
                    )
                )
    return rows

