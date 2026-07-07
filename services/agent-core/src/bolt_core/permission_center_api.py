"""Permission Center API router (M92). Read-only endpoint for the
desktop permission center panel.

GET /permission-center returns enriched permission list with Chinese
risk explanations and impact descriptions. Does NOT approve/reject.
"""
from fastapi import APIRouter

from bolt_core.permission_center import PermissionCenterService


def create_permission_center_router(permission_queue) -> APIRouter:
    router = APIRouter(tags=["permission-center"])
    service = PermissionCenterService(permission_queue)

    @router.get("/permission-center")
    def get_permission_center() -> dict:
        """获取中文权限中心摘要。只读。

        返回：
        - items: 权限列表（含风险等级、中文解释、影响说明）
        - total_pending: 待批准总数
        - high_risk_count / medium_risk_count / low_risk_count: 风险分级统计

        示例：GET /permission-center
        """
        return service.get_summary().to_dict()

    return router
