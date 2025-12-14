from __future__ import annotations

from it2ui.domain.models import SessionRow
from it2ui.domain.search import filter_and_rank


def _row(session_id: str, name: str) -> SessionRow:
    return SessionRow(
        window_id="w",
        window_index=1,
        tab_id="t",
        tab_index=1,
        session_id=session_id,
        name=name,
        is_active=False,
    )


def test_filter_and_rank_empty_query_returns_all() -> None:
    rows = [_row("s1", "alpha"), _row("s2", "bravo")]
    assert filter_and_rank(rows, "") == rows


def test_filter_and_rank_substring_beats_fuzzy() -> None:
    rows = [_row("s1", "prod-api"), _row("s2", "development")]
    out = filter_and_rank(rows, "prod")
    assert out[0].session_id == "s1"


def test_filter_and_rank_fuzzy_matches_typo() -> None:
    rows = [_row("s1", "kubernetes"), _row("s2", "database")]
    out = filter_and_rank(rows, "kubernets")
    assert any(r.session_id == "s1" for r in out)
