"""Desktop Beta Dogfood API (M100). Read-only grand review gate endpoint."""
from fastapi import APIRouter

from bolt_core.desktop_beta_dogfood import DesktopBetaDogfoodService


def create_desktop_beta_dogfood_router() -> APIRouter:
    router = APIRouter(tags=["desktop-beta-dogfood"])

    @router.get("/desktop-beta-dogfood")
    def desktop_beta_dogfood() -> dict:
        """运行桌面 Beta Dogfood 大复盘。只读。

        检查 M91-M99 所有面板的正确性、安全性和产品完备性。
        示例：GET /desktop-beta-dogfood
        """
        return DesktopBetaDogfoodService().run().to_dict()

    return router
