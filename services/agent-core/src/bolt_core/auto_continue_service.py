"""Auto-continue settings for the autonomous loop."""
from __future__ import annotations


class AutoContinueService:
    """Store auto-continue state with a strict round cap."""

    def __init__(self) -> None:
        self._enabled = False
        self._max_rounds = 5

    def set_auto_continue(self, enabled: bool, max_rounds: int = 5) -> dict:
        safe_rounds = max(1, min(int(max_rounds), 5))
        self._enabled = bool(enabled)
        self._max_rounds = safe_rounds
        return {
            "enabled": self._enabled,
            "max_rounds": self._max_rounds,
            "message": "自动继续已开启" if self._enabled else "自动继续已关闭",
        }

    def get_status(self) -> dict:
        return {
            "enabled": self._enabled,
            "max_rounds": self._max_rounds,
        }
