"""M122 data migration readiness API. Read-only."""
from fastapi import APIRouter

from bolt_core.data_migration import DataMigrationReadinessService


def create_data_migration_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["reliability"])

    @router.get("/reliability/data-migration")
    def data_migration_review() -> dict:
        result = DataMigrationReadinessService(project_dir).review()
        return {
            "review": result.to_dict(),
            "disclaimer": "只读数据迁移准备度检查，不会执行迁移、写入数据或批准权限。",
        }

    return router
