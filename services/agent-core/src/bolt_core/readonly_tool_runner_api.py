"""Read-only Tool Runner API. Execute safe read-only operations with path validation."""
from fastapi import APIRouter, HTTPException

from bolt_core.readonly_tool_runner import ReadOnlyToolRunner
from bolt_core.tool_registry import ToolRegistry


def create_readonly_tool_runner_router(
    registry: ToolRegistry | None = None, project_dir: str = "."
) -> APIRouter:
    """创建只读工具运行器 API 路由。"""
    if registry is None:
        registry = ToolRegistry()
    runner = ReadOnlyToolRunner(registry=registry, project_dir=project_dir)

    router = APIRouter(tags=["tools"])

    @router.post("/tools/readonly/run")
    def run_readonly_tool(payload: dict) -> dict:
        """执行只读工具操作。仅限已注册的 read_only 工具。所有输出经过安全检查和脱敏。
        
        请求体: { "tool_id": "read_file", "operation": "read_file", "params": {"path": "README.md"} }
        """
        tool_id = str(payload.get("tool_id", "")).strip()
        if not tool_id:
            raise HTTPException(status_code=400, detail="tool_id 不能为空")

        operation = str(payload.get("operation", "")).strip()
        if not operation:
            raise HTTPException(status_code=400, detail="operation 不能为空")

        params = payload.get("params", {})
        if not isinstance(params, dict):
            raise HTTPException(status_code=400, detail="params 必须是一个对象")

        result = runner.run(tool_id=tool_id, operation=operation, params=params)
        return {
            "result": result.to_dict(),
            "disclaimer": "只读运行器仅执行已注册的只读工具。所有路径受限于项目目录，敏感内容已脱敏。不执行写入/危险操作。",
        }

    return router
