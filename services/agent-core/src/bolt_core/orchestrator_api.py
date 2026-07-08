"""Orchestrator API router. Wires 5 roles into a coherent execution pipeline."""
from fastapi import APIRouter, HTTPException

from bolt_core.orchestrator_engine import OrchestratorEngine


def create_orchestrator_router() -> APIRouter:
    router = APIRouter(tags=["orchestrator"])

    @router.post("/orchestrator/run")
    def run_orchestration(payload: dict) -> dict:
        """运行编排流水线：Planner → Researcher → Builder → Reviewer → SkillLearner。

        payload: { task_description, workspace }
        """
        task_description = str(payload.get("task_description", "")).strip()
        workspace = str(payload.get("workspace", "")).strip()

        if not task_description:
            raise HTTPException(status_code=400, detail="task_description 不能为空")
        if not workspace:
            raise HTTPException(status_code=400, detail="workspace 不能为空")

        engine = OrchestratorEngine()
        result = engine.orchestrate(task_description, workspace)
        return {
            "task_description": result.task_description,
            "rounds": result.rounds,
            "final_verdict": result.final_verdict,
            "builder_output": result.builder_output,
            "review_findings": result.review_findings,
            "proposals": result.proposals,
            "trace": result.trace,
        }

    @router.get("/orchestrator/roles")
    def list_roles() -> dict:
        """列出 5 个角色及其状态。只读。"""
        return {
            "roles": [
                {"id": "planner", "name_cn": "规划师", "status": "ready"},
                {"id": "researcher", "name_cn": "研究员", "status": "ready"},
                {"id": "builder", "name_cn": "构建师", "status": "ready"},
                {"id": "reviewer", "name_cn": "审查员", "status": "ready"},
                {"id": "skill_learner", "name_cn": "技能学习器", "status": "ready"},
            ],
            "pipeline": "Planner → Researcher → Builder → Reviewer → SkillLearner",
        }

    return router
