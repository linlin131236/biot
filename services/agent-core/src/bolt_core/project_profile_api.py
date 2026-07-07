"""Project Profile API router. Read-only project portrait."""
from fastapi import APIRouter, Query

from bolt_core.project_profile import ProjectProfileService


def create_project_profile_router() -> APIRouter:
    router = APIRouter(tags=["project-profile"])
    service = ProjectProfileService(".")

    @router.get("/project/profile")
    def get_profile(workspace: str | None = Query(default=None)) -> dict:
        """Build and return project profile. Read-only, never writes."""
        if workspace:
            svc = ProjectProfileService(workspace)
            return svc.build().to_dict()
        return service.build().to_dict()

    return router
