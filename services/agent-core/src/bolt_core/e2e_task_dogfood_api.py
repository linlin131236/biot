"""E2E Task Dogfood API (M118). Read-only endpoints."""
import tempfile
from pathlib import Path
from fastapi import APIRouter
from bolt_core.e2e_task_dogfood import E2ETaskDogfoodService


def create_e2e_task_dogfood_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/e2e-dogfood/run")
    def run_e2e_dogfood() -> dict:
        with tempfile.TemporaryDirectory(prefix="bolt_e2e_") as tmp:
            summary = E2ETaskDogfoodService.run_all(Path(tmp))
            d = summary.to_dict()
        return {
            "summary": d,
            "verdict": d["verdict"],
            "disclaimer": "端到端任务复盘在临时目录中运行，不修改真实项目文件。",
        }

    return router
