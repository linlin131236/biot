"""Builder API router. Executes builder tasks and produces code change proposals.
Does NOT apply changes directly - all changes require PermissionGate approval.
"""
from fastapi import APIRouter, HTTPException

from bolt_core.builder_engine import BuilderEngine, BuilderTask


def create_builder_router() -> APIRouter:
    router = APIRouter(tags=["builder"])
    engine = BuilderEngine()

    @router.post("/builder/execute")
    def execute_builder_task(payload: dict) -> dict:
        """执行构建任务，产生代码变更提案。不直接写文件，需要 PermissionGate 审批后应用。

        payload: { task_id, description_cn, target_files, workspace?, proposed_changes? }
        """
        task_id = str(payload.get("task_id", "")).strip()
        description_cn = str(payload.get("description_cn", "")).strip()
        target_files = payload.get("target_files", [])
        workspace = str(payload.get("workspace", ""))
        proposed_changes = payload.get("proposed_changes", {})

        if not task_id:
            raise HTTPException(status_code=400, detail="task_id 不能为空")
        if not description_cn:
            raise HTTPException(status_code=400, detail="description_cn 不能为空")
        if not target_files:
            raise HTTPException(status_code=400, detail="target_files 不能为空")

        if not workspace:
            raise HTTPException(status_code=400, detail="workspace 不能为空")

        task = BuilderTask(
            task_id=task_id,
            description_cn=description_cn,
            target_files=target_files,
            workspace=workspace,
            proposed_changes=proposed_changes,
        )
        result = engine.execute_task(task)
        return {
            "task_id": task_id,
            "output": result.to_dict(),
            "proposals": {path: {"status": p.status, "error": p.error} for path, p in engine.list_proposals().items()},
        }

    @router.get("/builder/proposals")
    def list_proposals() -> dict:
        """列出所有构建提案。只读诊断。"""
        return {
            path: {"status": p.status, "error": p.error}
            for path, p in engine.list_proposals().items()
        }

    return router
