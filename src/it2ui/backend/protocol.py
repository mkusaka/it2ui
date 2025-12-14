from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

from it2ui.domain.models import Snapshot


@dataclass(frozen=True)
class BackendError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


@dataclass(frozen=True)
class BackendEvent:
    reason: str


class Backend(Protocol):
    async def snapshot(self) -> Snapshot: ...

    async def activate_session(self, session_id: str) -> None: ...

    def events(self) -> AsyncIterator[BackendEvent]: ...
