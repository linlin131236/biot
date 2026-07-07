"""M125 public beta readiness API. Read-only."""
from fastapi import APIRouter

from bolt_core.public_beta_readiness import PublicBetaReadinessService


def create_public_beta_readiness_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["reliability"])

    @router.get("/reliability/public-beta-readiness")
    def public_beta_review() -> dict:
        result = PublicBetaReadinessService(project_dir).review()
        return {
            "review": result.to_dict(),
            "disclaimer": "只读 Public Beta 准备度门禁，不会发布、push、tag、delete 或进入 M126。",
        }

    return router
