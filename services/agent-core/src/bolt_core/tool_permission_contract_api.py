"""Tool Permission Contract API. Evaluate permissions, verify approvals.
Read-only decision making, never executes tools or auto-approves."""
from fastapi import APIRouter, HTTPException

from bolt_core.tool_permission_contract import PermissionContractEngine
from bolt_core.tool_registry import ToolRegistry


def create_tool_permission_contract_router(registry: ToolRegistry | None = None) -> APIRouter:
    """创建工具权限契约 API 路由。"""
    if registry is None:
        registry = ToolRegistry()

    router = APIRouter(tags=["tools"])

    @router.post("/tools/permission/evaluate")
    def evaluate_permission(payload: dict) -> dict:
        """评估工具操作的权限需求。只产出决策，不执行工具。"""
        tool_id = str(payload.get("tool_id", "")).strip()
        if not tool_id:
            raise HTTPException(status_code=400, detail="tool_id 不能为空")

        operation = str(payload.get("operation", ""))
        decision = PermissionContractEngine.evaluate(
            tool_id=tool_id, operation=operation, registry=registry,
        )
        return {
            "decision": decision.to_dict(),
            "disclaimer": "权限评估仅产出决策建议，不执行任何工具操作，不自动批准任何权限。",
        }

    @router.post("/tools/permission/verify")
    def verify_approval(payload: dict) -> dict:
        """验证批准记录是否有效。拒绝 approved=true 绕过、agent self-approval、scope 不匹配。"""
        tool_id = str(payload.get("tool_id", "")).strip()
        if not tool_id:
            raise HTTPException(status_code=400, detail="tool_id 不能为空")

        approval_record = payload.get("approval", {})
        if not isinstance(approval_record, dict):
            raise HTTPException(status_code=400, detail="approval 必须是一个对象")

        # First evaluate what's needed
        decision = PermissionContractEngine.evaluate(
            tool_id=tool_id, registry=registry,
        )
        # Then verify the provided approval
        verification = PermissionContractEngine.verify_approval(decision, approval_record)
        return {
            "decision": decision.to_dict(),
            "verification": verification.to_dict(),
            "disclaimer": "验证仅检查批准记录的有效性，不执行任何工具操作。",
        }

    @router.get("/tools/permission/dangerous-ops")
    def list_dangerous_ops() -> dict:
        """列出所有被永久标记为危险的操作。只读。"""
        return PermissionContractEngine.list_dangerous_ops()

    return router
