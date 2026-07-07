"""Recovery policy API. Read-only reference only."""
from fastapi import APIRouter

from bolt_core.recovery_policy import RecoveryPolicyService


def create_recovery_policy_router(policy: RecoveryPolicyService) -> APIRouter:
    router = APIRouter(tags=["recovery"])

    @router.get("/recovery-policy")
    def recovery_policy() -> dict:
        """Return the recovery policy scenarios. Read-only, no execution."""
        return policy.list_scenarios()

    return router
