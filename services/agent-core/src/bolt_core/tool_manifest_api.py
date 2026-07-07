"""Tool Manifest API. Validate and query tool manifests. Read-only, never executes tools."""
from fastapi import APIRouter, HTTPException

from bolt_core.tool_manifest import ToolManifest, ToolManifestValidator
from bolt_core.tool_registry import ToolRegistry


def create_tool_manifest_router(registry: ToolRegistry | None = None) -> APIRouter:
    """创建工具 manifest API 路由。"""
    if registry is None:
        registry = ToolRegistry()

    router = APIRouter(tags=["tools"])

    @router.post("/tools/manifest/validate")
    def validate_manifest(payload: dict) -> dict:
        """验证工具 manifest 的结构完整性。只验证，不执行工具。"""
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="请求体必须是一个 JSON 对象")

        # Structural validation
        result = ToolManifestValidator.validate(payload)

        # Registry cross-validation (only if tool exists in registry)
        registry_result = None
        tool_id = str(payload.get("tool_id", ""))
        if tool_id and registry.get(tool_id):
            registry_result = ToolManifestValidator.validate_against_registry(payload, registry)

        response = {
            "structural": result.to_dict(),
        }
        if registry_result:
            response["registry_consistency"] = registry_result.to_dict()
            response["overall_valid"] = result.valid and registry_result.valid
        else:
            response["overall_valid"] = result.valid

        response["disclaimer"] = "Manifest 验证仅检查结构完整性，不执行任何工具操作。"
        return response

    @router.get("/tools/manifest/{tool_id}")
    def get_manifest(tool_id: str) -> dict:
        """查询工具 manifest 预览（从 registry 信息生成）。只读。"""
        tool_def = registry.get(tool_id)
        if tool_def is None:
            raise HTTPException(status_code=404, detail=f"工具 '{tool_id}' 未在注册表中找到")

        # Build a preview manifest from registry info
        preview = {
            "tool_id": tool_def.tool_id,
            "version": "0.1.0",
            "display_name": tool_def.display_name,
            "capability_summary": tool_def.description,
            "input_schema": tool_def.input_schema,
            "output_schema": tool_def.output_schema,
            "side_effect_level": tool_def.category,
            "permission_contract": {
                "required_level": tool_def.permission_required,
                "human_approval_required": not tool_def.allow_auto_run,
                "approval_scope": tool_def.tool_id,
            },
            "audit_requirements": {
                "log_calls": True,
                "log_results": True,
                "evidence_required": tool_def.risk_level in ("high", "critical"),
            },
            "rollback_support": tool_def.category in ("write", "dangerous"),
        }
        return {
            "manifest": preview,
            "disclaimer": "此预览从注册表信息自动生成。完整 manifest 需通过 /tools/manifest/validate 提交。",
        }

    return router
