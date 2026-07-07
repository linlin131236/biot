"""Multi-Agent Collaboration Eval API (M115). Read-only."""
from fastapi import APIRouter
from bolt_core.multi_agent_collaboration_eval import MultiAgentCollaborationEvalService


def create_multi_agent_collaboration_eval_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/multi-agent/run")
    def run_multi_agent_eval() -> dict:
        summary = MultiAgentCollaborationEvalService.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部多Agent协作评估通过" if d["all_passed"] else "❌ 存在未通过",
            "disclaimer": "多Agent协作评估仅验证角色边界定义，不执行真实Agent操作。",
        }

    return router
