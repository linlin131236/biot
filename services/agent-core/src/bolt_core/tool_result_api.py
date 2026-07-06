"""API serialization helpers for tool results."""
from bolt_core.tool_protocol import ToolResult


def tool_result_dict(result: ToolResult) -> dict[str, str | None]:
    return {
        "request_id": result.request_id,
        "status": result.status,
        "reason": result.reason,
        "output": result.output,
        "error": result.error,
    }
