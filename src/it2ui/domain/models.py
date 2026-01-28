from __future__ import annotations

import os
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
    working_directory: str
    command_line: str
    is_active: bool

    @property
    def display_name(self) -> str:
        name = self.name or "(unnamed)"
        return f"[{self.window_index}:{self.tab_index}] {name}"

    @property
    def display_cwd(self) -> str:
        return _abbrev_home(self.working_directory)


def _abbrev_home(path: str) -> str:
    raw = path.strip()
    if not raw:
        return ""
    home = os.path.expanduser("~").rstrip("/")
    if home and raw == home:
        return "~"
    if home and raw.startswith(home + "/"):
        return "~/" + raw.removeprefix(home + "/")
    return raw


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
        working_directory: str = ""
        command_line: str = ""

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
                        working_directory=session.working_directory,
                        command_line=session.command_line,
                        is_active=(snapshot.active_session_id == session.session_id),
                    )
                )
    return rows
