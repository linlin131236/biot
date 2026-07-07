"""Release readiness API. Read-only assessment only."""
from fastapi import APIRouter

from bolt_core.release_readiness import ReleaseReadinessService


def create_release_readiness_router(readiness: ReleaseReadinessService) -> APIRouter:
    router = APIRouter(tags=["release"])

    @router.get("/release-readiness")
    def release_readiness() -> dict:
        return readiness.assess()

    return router
