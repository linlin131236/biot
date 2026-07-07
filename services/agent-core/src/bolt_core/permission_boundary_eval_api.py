"""Permission Boundary Eval API (M114). Read-only endpoints."""
from fastapi import APIRouter

from bolt_core.permission_boundary_eval import PermissionBoundaryEvalService


def create_permission_boundary_eval_router() -> APIRouter:
    """创建权限边界评估 API 路由。全部只读。"""
    service = PermissionBoundaryEvalService()

    router = APIRouter(tags=["eval"])

    @router.get("/tools/eval/permission-boundary/run")
    def run_permission_boundary_eval() -> dict:
        """运行全部权限边界评估案例。只读，不执行真实操作。"""
        summary = service.run_all()
        d = summary.to_dict()
        return {
            "summary": d,
            "verdict": "✅ 全部权限边界评估通过" if d["all_passed"] else "❌ 存在未通过的评估案例",
            "disclaimer": "权限边界评估仅验证 PermissionContractEngine 决策正确性，不执行任何真实操作。",
        }

    return router
