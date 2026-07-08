"""Desktop settings API router (M151).

Provides authenticated endpoints for the renderer to read and write
desktop user preferences. API key is handled through a dedicated
endpoint and never appears in the settings payload.
"""
from pathlib import Path

from fastapi import APIRouter, Query

from bolt_core.desktop_settings import DesktopSettingsService


def create_desktop_settings_router(project_dir: str | Path | None = None) -> APIRouter:
    router = APIRouter(tags=["desktop-settings"])
    service = DesktopSettingsService(project_dir)

    @router.get("/desktop/settings")
    def get_desktop_settings() -> dict:
        """获取桌面设置状态。只返回配置状态，不回显 API key 明文。"""
        return service.get_status()

    @router.post("/desktop/settings")
    def update_desktop_settings(payload: dict) -> dict:
        """保存桌面设置（主题、语言、默认工作区）。"""
        return service.update(payload)

    @router.post("/desktop/settings/api-key")
    def save_api_key(payload: dict) -> dict:
        """保存 API key。请求体中包含 key，响应中不返回 key。"""
        api_key = str(payload.get("api_key", ""))
        if not api_key:
            return {"status": "error", "message": "API key 不能为空"}
        service.save_api_key(api_key)
        return {"status": "ok", "has_api_key": True}

    @router.delete("/desktop/settings/api-key")
    def delete_api_key() -> dict:
        """清除已保存的 API key。"""
        service.delete_api_key()
        return {"status": "ok", "has_api_key": False}

    @router.post("/desktop/settings/workspace-history")
    def add_workspace_history(payload: dict) -> dict:
        """添加工作区到最近打开列表。"""
        path = str(payload.get("path", ""))
        if not path:
            return {"status": "error", "message": "工作区路径不能为空"}
        return service.add_recent_workspace(path)

    return router
