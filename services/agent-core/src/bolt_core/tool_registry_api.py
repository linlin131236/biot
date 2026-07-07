"""Tool Registry API. Read-only tool definition management, never executes tools."""
from fastapi import APIRouter, HTTPException

from bolt_core.tool_registry import CATEGORIES, ToolDef, ToolRegistry


def create_tool_registry_router(registry: ToolRegistry | None = None) -> APIRouter:
    """创建工具注册表 API 路由。如不传 registry 则创建默认空注册表。"""
    if registry is None:
        registry = ToolRegistry()

    router = APIRouter(tags=["tools"])

    @router.get("/tools/registry/list")
    def list_tools(category: str | None = None) -> dict:
        """列出所有已注册工具。可选按类别过滤。只读，不执行工具。"""
        try:
            tools = registry.list(category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {
            "tools": [t.to_dict() for t in tools],
            "total": len(tools),
            "disclaimer": "此 API 仅返回工具定义，不执行任何工具操作。",
        }

    @router.get("/tools/registry/{tool_id}")
    def get_tool(tool_id: str) -> dict:
        """按 ID 查询工具定义。只读。"""
        tool = registry.get(tool_id)
        if tool is None:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_id}' 未在注册表中找到")
        return tool.to_dict()

    @router.post("/tools/registry/register")
    def register_tool(payload: dict) -> dict:
        """注册新工具。不执行工具。重复 ID 返回 409。"""
        tool_id = str(payload.get("tool_id", "")).strip()
        if not tool_id:
            raise HTTPException(status_code=400, detail="tool_id 不能为空")

        try:
            tool_def = ToolDef(
                tool_id=tool_id,
                display_name=str(payload.get("display_name", tool_id)),
                category=str(payload.get("category", "unknown")),
                description=str(payload.get("description", "")),
                input_schema=payload.get("input_schema", {}),
                output_schema=payload.get("output_schema", {}),
                permission_required=str(payload.get("permission_required", "none")),
                allow_auto_run=bool(payload.get("allow_auto_run", False)),
                risk_level=str(payload.get("risk_level", "low")),
            )
            registry.register(tool_def)
            return {"status": "registered", "tool": tool_def.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=409 if "已注册" in str(e) else 400, detail=str(e))

    @router.get("/tools/registry/summary")
    def registry_summary() -> dict:
        """返回工具注册表的分类统计概览。只读。"""
        return registry.summary()

    return router
