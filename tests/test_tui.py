from __future__ import annotations

from dataclasses import dataclass

import pytest
from textual.widgets import DataTable, Input

from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot
from it2ui.tui.app import It2uiApp


@dataclass
class FakeBackend:
    activated: list[str]

    async def snapshot(self) -> Snapshot:  # pragma: no cover
        raise AssertionError("not used")

    async def activate_session(self, session_id: str) -> None:
        self.activated.append(session_id)


def _snapshot(names: list[str]) -> Snapshot:
    sessions = [
        Snapshot.SessionSnapshot(
            session_id=f"s{i}",
            name=name,
            working_directory=f"/repo/{name}",
            command_line=f"cmd {name}",
        )
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
    backend = FakeBackend(activated=[])
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
async def test_query_change_resets_selection_to_top() -> None:
    backend = FakeBackend(activated=[])
    app = It2uiApp(backend=backend, initial_snapshot=_snapshot(["install", "other", "third"]))

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await pilot.press("down")
        await pilot.pause(0)
        assert app.controller.state.selected_index == 1

        await pilot.press("i")
        await pilot.pause(0.05)
        assert app.controller.state.selected_index == 0


@pytest.mark.asyncio
async def test_enter_activates_selected_session_from_input() -> None:
    backend = FakeBackend(activated=[])
    app = It2uiApp(backend=backend, initial_snapshot=_snapshot(["install", "other"]))

    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        for ch in "install":
            await pilot.press(ch)
        await pilot.pause(0.05)

        await pilot.press("enter")
        await pilot.pause(0.2)

    assert backend.activated == ["s1"]


@pytest.mark.asyncio
async def test_ctrl_c_requires_double_press() -> None:
    backend = FakeBackend(activated=[])
    exited = False
    toasts: list[str] = []

    class TestApp(It2uiApp):
        def exit(
            self, result: object | None = None, return_code: int = 0, message: object | None = None
        ) -> None:
            nonlocal exited
            exited = True

        def notify(self, message: object, *args: object, **kwargs: object) -> None:  # noqa: ANN401
            toasts.append(str(message))

    app = TestApp(backend=backend, initial_snapshot=_snapshot(["one"]))

    async with app.run_test() as pilot:
        await pilot.pause(0)

        await pilot.press("ctrl+c")
        await pilot.pause(0)
        assert exited is False
        assert any("Press Ctrl+C again to quit" in m for m in toasts)

        await pilot.press("ctrl+c")
        await pilot.pause(0)
        assert exited is True
