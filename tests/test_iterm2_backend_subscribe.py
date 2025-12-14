from __future__ import annotations

from dataclasses import dataclass

import pytest

from it2ui.backend.iterm2_backend import _subscribe_session_variables


@dataclass
class _Token:
    value: int


class _Notifications:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, str]] = []
        self._i = 0

    async def async_subscribe_to_variable_change_notification(
        self,
        connection: object,
        callback: object,  # noqa: ARG002
        scope: object,
        name: str,
        identifier: str,
    ) -> _Token:
        self._i += 1
        self.calls.append((scope, name, identifier))
        return _Token(self._i)


class _Variables:
    class VariableScopes:
        SESSION = "SESSION"


class _FakeIterm2:
    def __init__(self) -> None:
        self.notifications = _Notifications()
        self.variables = _Variables()


@pytest.mark.asyncio
async def test_subscribe_session_variables_uses_iterm2_variables_scope() -> None:
    iterm2 = _FakeIterm2()
    tokens: list[object] = []

    async def on_change(_connection: object, _notification: object) -> None:
        return

    await _subscribe_session_variables(
        iterm2=iterm2,
        connection=object(),
        session_id="s1",
        on_change=on_change,
        tokens=tokens,
    )

    assert iterm2.notifications.calls
    assert all(scope == "SESSION" for scope, _name, _sid in iterm2.notifications.calls)
    assert all(sid == "s1" for _scope, _name, sid in iterm2.notifications.calls)
    assert len(tokens) == len(iterm2.notifications.calls)
