"""Multi-Agent Recovery API."""
from fastapi import APIRouter, HTTPException
from bolt_core.multi_agent_recovery import MultiAgentRecoveryService


def create_multi_agent_recovery_router() -> APIRouter:
    router = APIRouter(tags=["multi-agent-recovery"])
    service = MultiAgentRecoveryService()

    @router.get("/recovery/scenarios")
    def list_scenarios() -> list[dict]:
        return service.scenario_options()

    @router.post("/recovery/plans")
    def create_plan(payload: dict) -> dict:
        plan = service.classify_and_suggest(
            scenario=payload.get("scenario", "unknown_failure"),
            description_cn=payload.get("description_cn", ""),
            source_refs=payload.get("source_refs"),
        )
        return plan.to_dict()

    @router.get("/recovery/plans")
    def list_plans() -> list[dict]:
        return [p.to_dict() for p in service.list_plans()]

    @router.get("/recovery/plans/{recovery_id}")
    def get_plan(recovery_id: str) -> dict:
        p = service.get_plan(recovery_id)
        if p is None:
            raise HTTPException(404, f"未找到恢复计划：{recovery_id}")
        return p.to_dict()

    return router
