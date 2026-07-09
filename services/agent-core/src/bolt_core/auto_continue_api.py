"""Auto-continue API router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bolt_core.auto_continue_service import AutoContinueService
from bolt_core.gate_freeze_service import GateFrozenError, GateFreezeService, get_global_gate_freeze_service


def create_auto_continue_router(
    service: AutoContinueService | None = None,
    gate_service: GateFreezeService | None = None,
) -> APIRouter:
    router = APIRouter(tags=["auto-continue"])
    auto_continue_service = service or AutoContinueService()
    gate = gate_service or get_global_gate_freeze_service()

    @router.post("/orchestrator/auto-continue")
    def auto_continue(payload: dict) -> dict:
        """开启或关闭自动继续。Gate 冻结时拒绝变更。"""
        try:
            gate.assert_not_frozen()
        except GateFrozenError as exc:
            raise HTTPException(status_code=423, detail=f"Gate 已冻结：{exc}") from exc

        enabled = bool(payload.get("enabled", False))
        max_rounds = int(payload.get("max_rounds", 5))
        return auto_continue_service.set_auto_continue(enabled, max_rounds)

    @router.get("/orchestrator/auto-continue")
    @router.get("/orchestrator/auto-continue/status")
    def get_auto_continue() -> dict:
        """读取自动继续状态。"""
        return auto_continue_service.get_status()

    return router
