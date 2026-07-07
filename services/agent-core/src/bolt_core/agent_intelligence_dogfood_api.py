"""Agent Intelligence Dogfood API (M120). Read-only comprehensive review gate."""
from fastapi import APIRouter
from bolt_core.agent_intelligence_dogfood import AgentIntelligenceDogfoodService


def create_agent_intelligence_dogfood_router() -> APIRouter:
    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/agent-intelligence/dogfood")
    def agent_intelligence_review() -> dict:
        service = AgentIntelligenceDogfoodService()
        result = service.review()
        d = result.to_dict()
        return {
            "dogfood_result": d,
            "verdict": "✅ V7 智能Agent评估全部通过" if d["all_passed"] else "❌ V7 存在P1失败项",
            "disclaimer": "此为 M120 Agent Intelligence Dogfood 大复盘结果。V7终点，等待爸爸复审。未进入M121。",
        }

    return router
