from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.core.player import Trainer


class AIStrategy(Protocol):
    def get_choice(self, trainer: Trainer, rival: Trainer) -> str | None: ...
