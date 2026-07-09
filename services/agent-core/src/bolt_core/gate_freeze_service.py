"""Gate freeze state shared by approval and autonomous-loop surfaces."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class GateFreezeState:
    frozen: bool = False
    reason: str = ""
    frozen_at: float = 0.0
    freeze_count: int = 0


_GLOBAL_STATE = GateFreezeState()


class GateFreezeService:
    """Shared freeze gate. When frozen, write/apply/auto-loop actions must stop."""

    def __init__(self, state: GateFreezeState | None = None) -> None:
        self._state = state or _GLOBAL_STATE

    def freeze(self, reason: str = "") -> dict:
        self._state.frozen = True
        self._state.reason = reason.strip() or "生产冻结"
        self._state.frozen_at = time.time()
        self._state.freeze_count += 1
        return self.get_status()

    def unfreeze(self) -> dict:
        self._state.frozen = False
        self._state.reason = ""
        self._state.frozen_at = 0.0
        return {
            **self.get_status(),
            "message": "Gate 已解除冻结",
        }

    def is_frozen(self) -> bool:
        return self._state.frozen

    def assert_not_frozen(self) -> None:
        if self._state.frozen:
            raise GateFrozenError(self._state.reason or "Gate 已冻结")

    def get_status(self) -> dict:
        return {
            "frozen": self._state.frozen,
            "reason": self._state.reason if self._state.frozen else "",
            "frozen_at": self._state.frozen_at if self._state.frozen else 0.0,
            "freeze_count": self._state.freeze_count,
        }


class GateFrozenError(RuntimeError):
    """Raised when a gated operation is attempted while the gate is frozen."""


def get_global_gate_freeze_service() -> GateFreezeService:
    return GateFreezeService(_GLOBAL_STATE)
