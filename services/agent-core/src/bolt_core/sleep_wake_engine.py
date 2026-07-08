"""SleepWakeEngine: manages agent idle/sleep/wake lifecycle.
M164: Sleep/Wake mode for autonomous operation.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Optional


class SleepState(str, Enum):
    AWAKE = "awake"
    SLEEPING = "sleeping"
    WAKING = "waking"


class SleepWakeEngine:
    """Manages agent sleep/wake lifecycle."""

    def __init__(self) -> None:
        self._state = SleepState.AWAKE
        self._sleep_start: float = 0
        self._wake_trigger: str = ""
        self._history: list[dict] = []

    def sleep(self, duration_seconds: int = 60, reason: str = "") -> dict:
        """Enter sleep mode for duration_seconds."""
        self._state = SleepState.SLEEPING
        self._sleep_start = time.time()
        entry = {
            "action": "sleep",
            "reason": reason or "空闲待机",
            "duration_seconds": duration_seconds,
            "ts": self._sleep_start,
        }
        self._history.append(entry)
        return {
            "state": self._state.value,
            "sleep_start": self._sleep_start,
            "duration_seconds": duration_seconds,
            "reason": entry["reason"],
        }

    def wake(self, trigger: str = "") -> dict:
        """Wake from sleep mode."""
        if self._state != SleepState.SLEEPING:
            return {
                "state": self._state.value,
                "message": f"当前状态为 {self._state.value}，无需唤醒",
            }
        self._state = SleepState.AWAKE
        self._wake_trigger = trigger or "manual"
        entry = {
            "action": "wake",
            "trigger": self._wake_trigger,
            "ts": time.time(),
        }
        self._history.append(entry)
        return {
            "state": self._state.value,
            "trigger": self._wake_trigger,
            "message": "已唤醒",
        }

    def get_status(self) -> dict:
        """Get current sleep/wake status."""
        return {
            "state": self._state.value,
            "is_sleeping": self._state == SleepState.SLEEPING,
            "wake_trigger": self._wake_trigger,
            "history_count": len(self._history),
            "history": self._history[-5:],
        }
