from __future__ import annotations

from dataclasses import dataclass

import pytest

from it2ui.backend.protocol import PaneDirection
from it2ui.domain.controller import ItwmController
from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot


@dataclass
class FakeBackend:
    activated: list[str]
    moved: list[PaneDirection]
    pane_ok: bool = True

    async def snapshot(self) -> Snapshot:  # pragma: no cover
        raise AssertionError("not used")

    async def activate_session(self, session_id: str) -> None:
        self.activated.append(session_id)

    async def select_pane(self, direction: PaneDirection) -> bool:
        self.moved.append(direction)
        return self.pane_ok


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
                            Snapshot.SessionSnapshot(session_id="s1", name="alpha"),
                            Snapshot.SessionSnapshot(session_id="s2", name="bravo"),
                        ],
                    )
                ],
            )
        ],
        active_session_id="s1",
    )


@pytest.mark.asyncio
async def test_activate_selected_calls_backend() -> None:
    backend = FakeBackend(activated=[], moved=[])
    c = ItwmController(backend=backend, initial_snapshot=_snapshot())
    await c.activate_selected()
    assert backend.activated == ["s1"]


@pytest.mark.asyncio
async def test_move_pane_uses_direction_and_handles_no_pane() -> None:
    backend = FakeBackend(activated=[], moved=[], pane_ok=False)
    c = ItwmController(backend=backend, initial_snapshot=_snapshot())
    await c.move_pane(PaneDirection.LEFT)
    assert backend.moved == [PaneDirection.LEFT]
    assert c.state.status == "No pane in that direction"
