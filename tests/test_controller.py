from __future__ import annotations

from dataclasses import dataclass

import pytest

from it2ui.domain.controller import ItwmController
from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot


@dataclass
class FakeBackend:
    activated: list[str]

    async def snapshot(self) -> Snapshot:  # pragma: no cover
        raise AssertionError("not used")

    async def activate_session(self, session_id: str) -> None:
        self.activated.append(session_id)


def _snapshot() -> Snapshot:
    return Snapshot(
        windows=[
            WindowSnapshot(
                window_id="w1",
                window_index=1,
                tabs=[
                    TabSnapshot(
                        tab_id="t1",
                        tab_index=1,
                        sessions=[
                            Snapshot.SessionSnapshot(
                                session_id="s1",
                                name="alpha",
                                working_directory="/repo/a",
                                command_line="zsh",
                            ),
                            Snapshot.SessionSnapshot(
                                session_id="s2",
                                name="bravo",
                                working_directory="/repo/b",
                                command_line="vim",
                            ),
                        ],
                    )
                ],
            )
        ],
        active_session_id="s1",
    )


@pytest.mark.asyncio
async def test_activate_selected_calls_backend() -> None:
    backend = FakeBackend(activated=[])
    c = ItwmController(backend=backend, initial_snapshot=_snapshot())
    await c.activate_selected()
    assert backend.activated == ["s1"]
