from __future__ import annotations

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
                            Snapshot.SessionSnapshot(session_id="s1", name="alpha"),
                            Snapshot.SessionSnapshot(session_id="s2", name="bravo"),
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
