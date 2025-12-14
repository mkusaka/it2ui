from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from it2ui.backend.protocol import BackendError, PaneDirection
from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot


def _safe_session_name(session: Any) -> str:
    for attr in ("name", "auto_name", "autoName", "title"):
        value = getattr(session, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    try:
        return str(session)
    except Exception:
        return ""


@dataclass
class Iterm2Backend:
    connection: Any

    async def snapshot(self) -> Snapshot:
        try:
            import iterm2
        except Exception as e:
            raise BackendError(
                "Failed to import iterm2. Run inside iTerm2 and ensure dependencies are installed."
            ) from e

        try:
            app = await iterm2.async_get_app(self.connection)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(
                "Failed to connect to iTerm2 Python API. "
                "Enable `Prefs > General > Magic > Enable Python API`, then retry and allow the prompt."
            ) from e

        windows: list[WindowSnapshot] = []

        current_session_id = self._current_session_id(app)

        try:
            iterm_windows: Iterable[Any] = getattr(app, "terminal_windows", None) or getattr(
                app, "windows", []
            )
        except Exception:
            iterm_windows = []

        for w_index, window in enumerate(iterm_windows, start=1):
            window_id = _string_id(
                getattr(window, "window_id", None) or getattr(window, "id", None)
            )
            tab_snaps: list[TabSnapshot] = []

            tabs: Iterable[Any] = getattr(window, "tabs", []) or []
            for t_index, tab in enumerate(tabs, start=1):
                tab_id = _string_id(getattr(tab, "tab_id", None) or getattr(tab, "id", None))
                sessions: list[Snapshot.SessionSnapshot] = []

                tab_sessions: Iterable[Any] = getattr(tab, "sessions", []) or []
                for session in tab_sessions:
                    session_id = _string_id(
                        getattr(session, "session_id", None) or getattr(session, "id", None)
                    )
                    sessions.append(
                        Snapshot.SessionSnapshot(
                            session_id=session_id,
                            name=_safe_session_name(session),
                        )
                    )

                tab_snaps.append(
                    TabSnapshot(
                        tab_id=tab_id,
                        tab_index=t_index,
                        sessions=sessions,
                    )
                )

            windows.append(
                WindowSnapshot(
                    window_id=window_id or str(w_index),
                    window_index=w_index,
                    tabs=tab_snaps,
                )
            )

        return Snapshot(windows=windows, active_session_id=current_session_id)

    async def activate_session(self, session_id: str) -> None:
        session = await self._find_session_by_id(session_id)
        if session is None:
            raise BackendError(f"Session not found: {session_id}")

        try:
            await session.async_activate(select_tab=True, order_window_front=True)
        except Exception as e:
            raise BackendError(
                "Failed to activate session. Ensure iTerm2 is running and the Python API is permitted."
            ) from e

    async def select_pane(self, direction: PaneDirection) -> bool:
        tab = await self._current_tab()
        if tab is None:
            return False

        try:
            import iterm2
        except Exception as e:
            raise BackendError("Failed to import iterm2.") from e

        tab_mod: Any = getattr(iterm2, "tab")
        nav: Any = getattr(tab_mod, "NavigationDirection")
        mapping = {
            PaneDirection.LEFT: getattr(nav, "LEFT"),
            PaneDirection.DOWN: getattr(nav, "DOWN"),
            PaneDirection.UP: getattr(nav, "UP"),
            PaneDirection.RIGHT: getattr(nav, "RIGHT"),
        }

        try:
            await tab.async_select_pane_in_direction(mapping[direction])
            return True
        except Exception:
            return False

    async def _current_tab(self) -> Optional[Any]:
        try:
            import iterm2
        except Exception as e:
            raise BackendError("Failed to import iterm2.") from e

        try:
            app = await iterm2.async_get_app(self.connection)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(
                "Failed to connect to iTerm2 Python API. "
                "Enable `Prefs > General > Magic > Enable Python API`, then retry and allow the prompt."
            ) from e

        window = getattr(app, "current_terminal_window", None)
        if window is None:
            return None
        tab = getattr(window, "current_tab", None)
        return tab

    async def _find_session_by_id(self, session_id: str) -> Optional[Any]:
        try:
            import iterm2
        except Exception as e:
            raise BackendError("Failed to import iterm2.") from e

        try:
            app = await iterm2.async_get_app(self.connection)  # type: ignore[attr-defined]
        except Exception as e:
            raise BackendError(
                "Failed to connect to iTerm2 Python API. "
                "Enable `Prefs > General > Magic > Enable Python API`, then retry and allow the prompt."
            ) from e

        try:
            iterm_windows: Iterable[Any] = getattr(app, "terminal_windows", None) or getattr(
                app, "windows", []
            )
        except Exception:
            iterm_windows = []

        for window in iterm_windows:
            for tab in getattr(window, "tabs", []) or []:
                for session in getattr(tab, "sessions", []) or []:
                    sid = _string_id(
                        getattr(session, "session_id", None) or getattr(session, "id", None)
                    )
                    if sid == session_id:
                        return session
        return None

    def _current_session_id(self, app: Any) -> Optional[str]:
        try:
            window = getattr(app, "current_terminal_window", None)
            tab = getattr(window, "current_tab", None) if window is not None else None
            session = getattr(tab, "current_session", None) if tab is not None else None
            sid = _string_id(
                getattr(session, "session_id", None) or getattr(session, "id", None)
                if session is not None
                else None
            )
            return sid or None
        except Exception:
            return None


def _string_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return ""
