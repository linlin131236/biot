"""Settings Tools API (M99). Self-contained read-only configuration view."""
from fastapi import APIRouter


def create_settings_tools_router() -> APIRouter:
    router = APIRouter(tags=["settings-tools"])

    @router.get("/settings-tools")
    def get_settings_tools() -> dict:
        return {
            "budget": {},
            "model_config": {"provider": "配置于 Agent Core 环境变量中", "status": "已就绪"},
            "tool_policy": {"mode": "PermissionGate 管控", "description": "工具执行需通过权限审批"},
        }

    return router
