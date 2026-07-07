"""Failure Recovery Dogfood API (M119). Read-only."""
from fastapi import APIRouter
from bolt_core.failure_recovery_dogfood import FailureRecoveryDogfoodService


def create_failure_recovery_dogfood_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/failure-recovery/run")
    def run_recovery_eval() -> dict:
        summary = FailureRecoveryDogfoodService.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": d["verdict"],
            "disclaimer": "失败恢复狗粮评估不自动修复任何问题（auto_fix_allowed=false）。",
        }

    return router
