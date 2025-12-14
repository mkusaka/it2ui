from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from it2ui.domain.models import Snapshot


class PaneDirection(Enum):
    LEFT = "left"
    DOWN = "down"
    UP = "up"
    RIGHT = "right"


@dataclass(frozen=True)
class BackendError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


class Backend(Protocol):
    async def snapshot(self) -> Snapshot: ...

    async def activate_session(self, session_id: str) -> None: ...

    async def select_pane(self, direction: PaneDirection) -> bool: ...
