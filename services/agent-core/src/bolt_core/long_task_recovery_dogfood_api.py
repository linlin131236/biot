"""Long Task Recovery Dogfood API. Read-only readiness check, never auto-executes."""
from fastapi import APIRouter

from bolt_core.long_task_recovery_dogfood import LongTaskRecoveryDogfoodService


def create_long_task_recovery_dogfood_router() -> APIRouter:
    """Create router for long task recovery dogfood assessment.

    The assess endpoint runs all 9 readiness checks for the M61-M68 closed loop.
    It NEVER executes recovery, NEVER approves permissions.
    """
    router = APIRouter(tags=["dogfood"])
    service = LongTaskRecoveryDogfoodService()

    @router.get("/dogfood/long-task-recovery")
    def assess_recovery_readiness() -> dict:
        """Run long task recovery dogfood assessment.

        Checks: task graph, state machine, pause/resume permissions,
        steering safety, budget blocking, failure classifier Chinese diagnosis,
        retry loop safety, PermissionGate integrity, traceability.

        Returns a readiness report with pass/fail per check, Chinese summary,
        and overall readiness status (ready/not_ready/needs_review).

        This is a READ-ONLY assessment. It does NOT execute any recovery actions.
        """
        report = service.assess()
        return report.to_dict()

    return router
