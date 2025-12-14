from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from it2ui.backend.protocol import BackendError, BackendEvent
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
                    working_directory = await _get_first_session_var(
                        session,
                        [
                            "session.path",
                            "session.workingDirectory",
                            "session.working_directory",
                            "session.currentDirectory",
                            "session.cwd",
                        ],
                    )
                    command_line = await _get_first_session_var(
                        session,
                        [
                            "session.commandLine",
                            "session.command_line",
                            "session.command",
                            "session.job",
                            "session.foregroundCommandLine",
                            "session.foregroundJob",
                        ],
                    )
                    sessions.append(
                        Snapshot.SessionSnapshot(
                            session_id=session_id,
                            name=_safe_session_name(session),
                            working_directory=working_directory,
                            command_line=command_line,
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

    def events(self) -> AsyncIterator[BackendEvent]:
        return self._events()

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

    async def _events(self) -> AsyncIterator[BackendEvent]:
        try:
            import iterm2
        except Exception as e:
            raise BackendError(
                "Failed to import iterm2. Run inside iTerm2 and ensure dependencies are installed."
            ) from e

        queue: asyncio.Queue[BackendEvent] = asyncio.Queue()
        tokens: list[Any] = []

        async def subscribe(callback: Callable[[Any, Any], Any], name: str) -> None:
            fn = getattr(iterm2.notifications, name, None)
            if fn is None:
                return
            try:
                token = await fn(self.connection, callback)
            except Exception:
                return
            tokens.append(token)

        def emit(reason: str) -> None:
            with contextlib.suppress(Exception):
                queue.put_nowait(BackendEvent(reason=reason))

        async def on_layout_change(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("layout_change")

        async def on_focus_change(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("focus_change")

        async def on_new_session(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("new_session")
            session_id = _get_notification_session_id(notification)
            if session_id:
                await _subscribe_session_variables(
                    iterm2=iterm2,
                    connection=self.connection,
                    session_id=session_id,
                    on_change=on_variable_change,
                    tokens=tokens,
                )

        async def on_terminate_session(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("terminate_session")

        async def on_prompt(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("prompt")

        async def on_variable_change(connection: Any, notification: Any) -> None:  # noqa: ARG001
            emit("variable_change")

        await subscribe(on_layout_change, "async_subscribe_to_layout_change_notification")
        await subscribe(on_focus_change, "async_subscribe_to_focus_change_notification")
        await subscribe(on_new_session, "async_subscribe_to_new_session_notification")
        await subscribe(on_terminate_session, "async_subscribe_to_terminate_session_notification")
        await subscribe(on_prompt, "async_subscribe_to_prompt_notification")

        try:
            app = await iterm2.async_get_app(self.connection)  # type: ignore[attr-defined]
        except Exception:
            app = None

        if app is not None:
            session_ids = list(_iter_session_ids(app))
            for session_id in session_ids:
                await _subscribe_session_variables(
                    iterm2=iterm2,
                    connection=self.connection,
                    session_id=session_id,
                    on_change=on_variable_change,
                    tokens=tokens,
                )

        try:
            while True:
                yield await queue.get()
        finally:
            for token in tokens:
                with contextlib.suppress(Exception):
                    await iterm2.notifications.async_unsubscribe(  # type: ignore[no-untyped-call]
                        self.connection, token
                    )


def _string_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return ""


async def _get_first_session_var(session: Any, names: list[str]) -> str:
    for name in names:
        try:
            value: Any = await session.async_get_variable(name)
        except Exception:
            continue
        text = _to_text(value).strip()
        if text:
            return text
    return ""


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_to_text(v) for v in value)
    try:
        return str(value)
    except Exception:
        return ""


def _get_notification_session_id(notification: Any) -> str:
    for attr in ("session_id", "sessionId", "session"):
        value = getattr(notification, attr, None)
        if isinstance(value, str) and value:
            return value
        if value is not None and attr == "session":
            sid = getattr(value, "session_id", None) or getattr(value, "id", None)
            if isinstance(sid, str) and sid:
                return sid
    return ""


def _iter_session_ids(app: Any) -> Iterable[str]:
    try:
        iterm_windows: Iterable[Any] = getattr(app, "terminal_windows", None) or getattr(
            app, "windows", []
        )
    except Exception:
        return

    for window in iterm_windows:
        for tab in getattr(window, "tabs", []) or []:
            for session in getattr(tab, "sessions", []) or []:
                session_id = _string_id(
                    getattr(session, "session_id", None) or getattr(session, "id", None)
                )
                if session_id:
                    yield session_id


async def _subscribe_session_variables(
    *,
    iterm2: Any,
    connection: Any,
    session_id: str,
    on_change: Callable[[Any, Any], Any],
    tokens: list[Any],
) -> None:
    scope = getattr(iterm2, "VariableScopes", None)
    if scope is None:
        variables_mod = getattr(iterm2, "variables", None)
        scope = (
            getattr(variables_mod, "VariableScopes", None) if variables_mod is not None else None
        )
    if scope is None:
        return

    try:
        session_scope: Any = getattr(scope, "SESSION")
        session_scope_value: Any = getattr(session_scope, "value", session_scope)
    except Exception:
        return

    for name in [
        "session.path",
        "session.workingDirectory",
        "session.currentDirectory",
        "session.commandLine",
        "session.command",
        "session.foregroundCommandLine",
        "session.foregroundJob",
        "session.name",
        "session.title",
    ]:
        try:
            token = await iterm2.notifications.async_subscribe_to_variable_change_notification(
                connection,
                on_change,
                session_scope_value,
                name,
                session_id,
            )
        except Exception:
            continue
        tokens.append(token)
