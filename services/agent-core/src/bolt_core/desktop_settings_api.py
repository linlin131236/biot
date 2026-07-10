"""Desktop settings API router (M151).

Provides authenticated endpoints for the renderer to read and write
desktop user preferences. API key is handled through a dedicated
endpoint and never appears in the settings payload.
"""
from pathlib import Path

from fastapi import APIRouter, Query

from bolt_core.desktop_settings import DesktopSettingsService
from bolt_core.credential_lifecycle import CredentialConfigStore, CredentialLifecycle


def create_desktop_settings_router(
    project_dir: str | Path | None = None,
    *,
    credential_lifecycle: CredentialLifecycle | None = None,
    credential_configs: CredentialConfigStore | None = None,
    provider: str = "openai-compatible",
) -> APIRouter:
    router = APIRouter(tags=["desktop-settings"])
    service = DesktopSettingsService(project_dir)

    @router.get("/desktop/settings")
    def get_desktop_settings() -> dict:
        """获取桌面设置状态。只返回配置状态，不回显 API key 明文。"""
        status = service.get_status()
        if credential_configs is None:
            return status
        config = credential_configs.load(provider)
        status["has_api_key"] = (
            config.credential_state == "active"
            and config.active_credential_id is not None
        )
        status["credential_revision"] = config.revision
        return status

    @router.post("/desktop/settings")
    def update_desktop_settings(payload: dict) -> dict:
        """保存桌面设置（主题、语言、默认工作区）。"""
        return service.update(payload)

    @router.post("/desktop/settings/api-key")
    def save_api_key(payload: dict) -> dict:
        """保存 API key。请求体中包含 key，响应中不返回 key。"""
        api_key = str(payload.get("api_key", ""))
        revision = int(payload.get("revision", -1))
        if not api_key:
            return {"status": "error", "message": "API key 不能为空"}
        if credential_lifecycle is None or credential_configs is None:
            return {"status": "error", "message": "credential lifecycle unavailable"}
        current = credential_configs.load(provider)
        if current.credential_state == "active" and current.active_credential_id:
            state = credential_lifecycle.replace(provider, api_key, expected_revision=revision)
        else:
            state = credential_lifecycle.add(provider, api_key, expected_revision=revision)
        return {"status": "ok", "has_api_key": True, "revision": state.revision}

    @router.delete("/desktop/settings/api-key")
    def delete_api_key(revision: int = Query(...)) -> dict:
        """清除已保存的 API key。"""
        if credential_lifecycle is None or credential_configs is None:
            return {"status": "error", "message": "credential lifecycle unavailable"}
        state = credential_lifecycle.delete(provider, expected_revision=revision)
        return {"status": "ok", "has_api_key": False, "revision": state.revision}

    @router.post("/desktop/settings/workspace-history")
    def add_workspace_history(payload: dict) -> dict:
        """添加工作区到最近打开列表。"""
        path = str(payload.get("path", ""))
        if not path:
            return {"status": "error", "message": "工作区路径不能为空"}
        return service.add_recent_workspace(path)

    return router
