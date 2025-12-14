from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from itwm.domain.models import SessionRow


@dataclass(frozen=True)
class ScoredRow:
    row: SessionRow
    score: float


def _normalize(query: str) -> str:
    return query.strip().lower()


def _candidate_text(row: SessionRow) -> str:
    parts = [
        row.display_name,
        row.session_id,
        row.window_id,
        str(row.window_index),
        row.tab_id,
        str(row.tab_index),
    ]
    return " ".join(p for p in parts if p).lower()


def filter_and_rank(rows: Sequence[SessionRow], query: str) -> list[SessionRow]:
    q = _normalize(query)
    if not q:
        return list(rows)

    try:
        from rapidfuzz.fuzz import WRatio
    except Exception:
        return _filter_simple(rows, q)

    scored: list[ScoredRow] = []
    for row in rows:
        text = _candidate_text(row)
        if q in text:
            base = 100.0
            bonus = 10.0 if text.startswith(q) else 0.0
            scored.append(ScoredRow(row=row, score=base + bonus))
            continue
        score = float(WRatio(q, text))
        if score >= 40.0:
            scored.append(ScoredRow(row=row, score=score))

    scored.sort(key=lambda x: (-x.score, x.row.window_index, x.row.tab_index, x.row.display_name))
    return [s.row for s in scored]


def _filter_simple(rows: Iterable[SessionRow], q: str) -> list[SessionRow]:
    out: list[SessionRow] = []
    for row in rows:
        if q in _candidate_text(row):
            out.append(row)
    return out
