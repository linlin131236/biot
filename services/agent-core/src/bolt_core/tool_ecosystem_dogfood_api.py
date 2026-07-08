"""Tool Ecosystem Dogfood API (M110). Read-only review gate endpoint."""
from fastapi import APIRouter

from bolt_core.tool_ecosystem_dogfood import ToolEcosystemDogfoodService


def create_tool_ecosystem_dogfood_router() -> APIRouter:
    """创建工具生态 dogfood 复查 API 路由。"""
    service = ToolEcosystemDogfoodService()

    router = APIRouter(tags=["tools"])

    @router.get("/tools/ecosystem/dogfood")
    def dogfood_review() -> dict:
        """执行 M101-M109 全部门禁检查。只读。"""
        result = service.review()
        return {
            "dogfood_result": result.to_dict(),
            "verdict": "✅ V6 工具生态通过" if result.all_passed else "❌ V6 存在 P1 失败项",
            "disclaimer": "此为 M110 工具生态大复盘审查结果。如全部通过，V6 完成，等待用户复审。未进入 M111。",
        }

    return router
