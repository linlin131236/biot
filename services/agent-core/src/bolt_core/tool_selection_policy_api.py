"""Tool selection policy API. Classifies and validates, never executes."""
from fastapi import APIRouter, HTTPException

from bolt_core.tool_selection_policy import TOOL_CLASSES, ToolSelectionPolicy


def create_tool_selection_policy_router() -> APIRouter:
    router = APIRouter(tags=["tools"])

    @router.get("/tools/policy/summary")
    def policy_summary() -> dict:
        """Return a summary of tool classes and counts."""
        return ToolSelectionPolicy.summary()

    @router.get("/tools/policy/classify/{tool_name}")
    def classify_tool(tool_name: str) -> dict:
        """Classify a single tool."""
        return ToolSelectionPolicy.classify(tool_name)

    @router.get("/tools/policy/list")
    def list_tools(tool_class: str | None = None) -> list[dict]:
        """List registered tools, optionally filtered by class."""
        if tool_class and tool_class not in TOOL_CLASSES:
            raise HTTPException(status_code=400, detail=f"unknown tool class: {tool_class}")
        return ToolSelectionPolicy.list_tools(tool_class)

    @router.post("/tools/policy/select")
    def select_tools(payload: dict) -> dict:
        """Validate a tool selection. Returns per-tool permission requirements."""
        tool_names = payload.get("tools", [])
        if not isinstance(tool_names, list) or not tool_names:
            raise HTTPException(status_code=400, detail="tools list is required")
        reason = str(payload.get("reason", ""))
        return ToolSelectionPolicy.select([str(t) for t in tool_names], reason)

    return router
