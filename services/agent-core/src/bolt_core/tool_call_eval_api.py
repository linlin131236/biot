"""Tool Call Eval API (M111). Read-only endpoints for tool call evaluation results."""
from fastapi import APIRouter, HTTPException

from bolt_core.tool_call_eval import ToolCallEvalService


def create_tool_call_eval_router() -> APIRouter:
    """创建工具调用评估 API 路由。全部只读。"""
    service = ToolCallEvalService()

    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/cases")
    def list_eval_cases() -> dict:
        """列出所有评估案例。只读。"""
        return {
            "cases": service.list_cases(),
            "total": len(service.list_cases()),
            "disclaimer": "工具调用评估案例列表，不执行真实工具操作。",
        }

    @router.get("/tools/eval/cases/{case_id}")
    def get_eval_case(case_id: str) -> dict:
        """获取单个评估案例定义。只读。"""
        case = service.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"评估案例 '{case_id}' 不存在")
        return {"case": case}

    @router.get("/tools/eval/run")
    def run_all_evals() -> dict:
        """运行全部评估案例并返回汇总。只读，不执行真实工具。"""
        summary = service.run_all()
        return {
            "summary": summary.to_dict(),
            "verdict": "✅ 全部工具调用评估通过" if summary.to_dict()["all_passed"] else "❌ 存在未通过的评估案例",
        }

    @router.get("/tools/eval/run/{case_id}")
    def run_single_eval(case_id: str) -> dict:
        """运行单个评估案例。只读。"""
        result = service.run_single(case_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"评估案例 '{case_id}' 不存在")
        return {
            "result": result.to_dict(),
            "verdict": "✅ 通过" if result.overall_passed else "❌ 未通过",
        }

    return router
