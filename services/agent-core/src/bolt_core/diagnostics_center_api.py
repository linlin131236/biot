"""Diagnostics Center API (M94). Aggregates diagnostics + integrity into one endpoint."""
from fastapi import APIRouter


def create_diagnostics_center_router(diagnostics_service, integrity_service) -> APIRouter:
    router = APIRouter(tags=["diagnostics-center"])

    @router.get("/diagnostics-center")
    def get_diagnostics_center() -> dict:
        """获取诊断中心聚合摘要。只读。

        合并执行审计诊断和完整性检查结果。
        示例：GET /diagnostics-center
        """
        diags: list[dict] = []
        integ: list[dict] = []
        try:
            diags = diagnostics_service.list_diagnostics()
        except Exception:
            pass
        try:
            integ = integrity_service.list_integrity()
        except Exception:
            pass

        blockers = sum(1 for d in diags if d.get("severity") == "blocking") + \
                   sum(1 for i in integ if i.get("severity") == "blocking")
        warnings = sum(1 for d in diags if d.get("severity") == "warning") + \
                   sum(1 for i in integ if i.get("severity") == "warning")
        infos = sum(1 for d in diags if d.get("severity") == "info") + \
                sum(1 for i in integ if i.get("severity") == "info")

        return {
            "diagnostics": diags,
            "integrity": integ,
            "total_blockers": blockers,
            "total_warnings": warnings,
            "total_infos": infos,
        }

    return router
