from __future__ import annotations

from dataclasses import dataclass

import pytest
from textual.widgets import DataTable, Input

from it2ui.backend.protocol import PaneDirection
from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot
from it2ui.tui.app import It2uiApp


@dataclass
class FakeBackend:
    activated: list[str]
    moved: list[PaneDirection]

    async def snapshot(self) -> Snapshot:  # pragma: no cover
        raise AssertionError("not used")

    async def activate_session(self, session_id: str) -> None:
        self.activated.append(session_id)

    async def select_pane(self, direction: PaneDirection) -> bool:
        self.moved.append(direction)
        return True


def _snapshot(names: list[str]) -> Snapshot:
    sessions = [
        Snapshot.SessionSnapshot(session_id=f"s{i}", name=name)
        for i, name in enumerate(names, start=1)
    ]
    return Snapshot(
        windows=[
            WindowSnapshot(
                window_id="w1",
                window_index=1,
                tabs=[TabSnapshot(tab_id="t1", tab_index=1, sessions=sessions)],
            )
        ],
        active_session_id="s1",
    )


@pytest.mark.asyncio
async def test_search_input_is_visible_and_typing_filters() -> None:
    backend = FakeBackend(activated=[], moved=[])
    app = It2uiApp(backend=backend, initial_snapshot=_snapshot(["install", "other"]))

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        search = app.query_one("#search", Input)
        assert search.size.width > 0

        for ch in "install":
            await pilot.press(ch)
        await pilot.pause(0.05)

        assert search.value == "install"
        table = app.query_one("#table", DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_ctrl_q_requires_double_press() -> None:
    backend = FakeBackend(activated=[], moved=[])
    exited = False

    class TestApp(It2uiApp):
        def exit(
            self, result: object | None = None, return_code: int = 0, message: object | None = None
        ) -> None:
            nonlocal exited
            exited = True

    app = TestApp(backend=backend, initial_snapshot=_snapshot(["one"]))

    async with app.run_test() as pilot:
        await pilot.pause(0)

        await pilot.press("ctrl+q")
        await pilot.pause(0)
        assert exited is False
        assert "Press Ctrl+Q again to quit" in app.controller.state.status

        await pilot.press("ctrl+q")
        await pilot.pause(0)
        assert exited is True
