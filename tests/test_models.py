from __future__ import annotations

import os

from it2ui.domain.models import Snapshot, TabSnapshot, WindowSnapshot, rows_from_snapshot


def test_rows_from_snapshot_marks_active() -> None:
    snap = Snapshot(
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
        active_session_id="s2",
    )

    rows = rows_from_snapshot(snap)
    assert [r.session_id for r in rows] == ["s1", "s2"]
    assert [r.is_active for r in rows] == [False, True]
    assert rows[0].working_directory == "/repo/a"
    assert rows[1].command_line == "vim"


def test_display_cwd_abbrev_home() -> None:
    home = os.path.expanduser("~")
    snap = Snapshot(
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
                                working_directory=f"{home}/src/repo",
                                command_line="zsh",
                            ),
                        ],
                    )
                ],
            )
        ],
        active_session_id="s1",
    )
    rows = rows_from_snapshot(snap)
    assert rows[0].display_cwd.startswith("~/")
