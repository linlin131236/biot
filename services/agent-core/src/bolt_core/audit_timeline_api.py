"""Audit Timeline aggregation (M93). Read-only summary across all closures."""
from fastapi import APIRouter

from bolt_core.execution_audit_timeline import ExecutionAuditTimelineService
from bolt_core.task_closure_service import TaskClosureService


def create_audit_timeline_router(
    timeline_service: ExecutionAuditTimelineService,
    task_closure_service: TaskClosureService,
) -> APIRouter:
    router = APIRouter(tags=["audit-timeline"])

    @router.get("/audit-timeline")
    def audit_timeline_summary(
        closure_id: str | None = None,
        source: str | None = None,
    ) -> dict:
        """获取审计时间线摘要。只读。

        可传入 closure_id 过滤任务闭环。
        可传入 source 过滤事件来源（queue / handoff / closure / permission）。
        未传 closure_id 时返回最近 20 条时间线事件。
        示例：GET /audit-timeline?closure_id=xxx&source=queue
        """
        if closure_id:
            if task_closure_service.load(closure_id) is None:
                return {"events": [], "total": 0, "message_cn": "任务闭环不存在。"}
            events = timeline_service.for_closure(closure_id)
        else:
            # Collect events across all known closures (best-effort)
            all_events: list[dict] = []
            try:
                closures = task_closure_service.list_closures()
                for c in closures[:10]:
                    try:
                        evts = timeline_service.for_closure(c["id"])
                        all_events.extend(evts)
                    except Exception:
                        pass
                all_events.sort(key=lambda e: e.get("occurred_at", 0), reverse=True)
            except Exception:
                pass
            events = all_events[:20]

        if source:
            events = [e for e in events if e.get("source") == source]

        return {"events": events, "total": len(events), "closure_id": closure_id}

    return router
