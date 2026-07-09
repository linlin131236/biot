"""Gate Freeze API router."""
from __future__ import annotations

from fastapi import APIRouter

from bolt_core.gate_freeze_service import GateFreezeService, get_global_gate_freeze_service


def create_gate_freeze_router(service: GateFreezeService | None = None) -> APIRouter:
    router = APIRouter(tags=["gate-freeze"])
    gate_service = service or get_global_gate_freeze_service()

    @router.post("/gate/freeze")
    def freeze_gate(payload: dict) -> dict:
        """冻结 Gate。冻结后写入应用、自动继续等动作会被阻断。"""
        return gate_service.freeze(str(payload.get("reason", "")))

    @router.post("/gate/unfreeze")
    def unfreeze_gate() -> dict:
        """解除 Gate 冻结。"""
        return gate_service.unfreeze()

    @router.get("/gate/status")
    def gate_status() -> dict:
        """读取 Gate 冻结状态。"""
        return gate_service.get_status()

    return router
