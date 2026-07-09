"""Desktop beta ship readiness API."""
from __future__ import annotations

from fastapi import APIRouter

from bolt_core.desktop_beta_ship import DesktopBetaShipService


def create_desktop_beta_ship_router(project_dir: str = ".") -> APIRouter:
    router = APIRouter(tags=["desktop-beta-ship"])

    @router.get("/desktop/beta-ship")
    def desktop_beta_ship() -> dict:
        return DesktopBetaShipService(project_dir).review().to_dict()

    return router
