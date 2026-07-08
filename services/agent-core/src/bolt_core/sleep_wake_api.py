"""Sleep/Wake API router. Manages agent idle/sleep/wake lifecycle."""
from fastapi import APIRouter, HTTPException

from bolt_core.sleep_wake_engine import SleepWakeEngine


def create_sleep_wake_router() -> APIRouter:
    router = APIRouter(tags=["sleep-wake"])
    engine = SleepWakeEngine()

    @router.post("/sleep-wake/sleep")
    def sleep(payload: dict) -> dict:
        """进入待机模式。

        payload: { duration_seconds?, reason? }
        """
        duration = int(payload.get("duration_seconds", 60))
        reason = str(payload.get("reason", ""))
        return engine.sleep(duration, reason)

    @router.post("/sleep-wake/wake")
    def wake(payload: dict) -> dict:
        """从待机模式唤醒。

        payload: { trigger? }
        """
        trigger = str(payload.get("trigger", ""))
        return engine.wake(trigger)

    @router.get("/sleep-wake/status")
    def status() -> dict:
        """获取当前待机状态。只读。"""
        return engine.get_status()

    return router
