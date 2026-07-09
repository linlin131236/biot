"""Autonomous loop API router."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from bolt_core.autonomous_loop_service import AutonomousLoopService
from bolt_core.gate_freeze_service import GateFrozenError, GateFreezeService, get_global_gate_freeze_service


def create_autonomous_loop_router(
    service: AutonomousLoopService | None = None,
    gate_service: GateFreezeService | None = None,
) -> APIRouter:
    router = APIRouter(tags=["autonomous-loop"])
    loop_service = service or AutonomousLoopService()
    gate = gate_service or get_global_gate_freeze_service()

    @router.post("/orchestrator/autonomous-loop")
    def run_autonomous_loop(payload: dict) -> dict:
        """运行有轮数上限的端到端自主循环。Gate 冻结时拒绝启动。"""
        try:
            gate.assert_not_frozen()
        except GateFrozenError as exc:
            raise HTTPException(status_code=423, detail=f"Gate 已冻结：{exc}") from exc

        task_description = str(payload.get("task_description", "未命名任务")).strip()
        workspace = str(payload.get("workspace", ".")).strip()
        max_rounds = int(payload.get("max_rounds", 5))
        if not task_description:
            raise HTTPException(status_code=400, detail="task_description 不能为空")
        if not workspace:
            raise HTTPException(status_code=400, detail="workspace 不能为空")
        return loop_service.run_loop(task_description, workspace, max_rounds)

    return router
