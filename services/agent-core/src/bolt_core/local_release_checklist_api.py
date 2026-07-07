"""Local release checklist API. Read-only diagnostic only."""
from fastapi import APIRouter

from bolt_core.local_release_checklist import LocalReleaseChecklistService


def create_local_release_checklist_router(checklist_svc: LocalReleaseChecklistService) -> APIRouter:
    router = APIRouter(tags=["release"])

    @router.get("/local-release-checklist")
    def local_release_checklist() -> dict:
        """Return the local release checklist. Read-only. Does NOT execute any release action."""
        return checklist_svc.checklist()

    return router
