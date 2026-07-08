"""Task result summary builder. Extracted from task_closure_service.py (M158)."""
from __future__ import annotations

from bolt_core.task_closure_service import TaskClosureService as _TaskClosureService


class TaskResultSummaryBuilder:
    """Builds structured result summaries from TaskClosureService data.
    Does NOT execute tools, push, release, or approve permissions.
    """

    def __init__(self, service: _TaskClosureService | None = None) -> None:
        self._service = service

    def build(self, closure_id: str) -> dict:
        """Synthesize a structured result summary from closure data."""
        record = self._service._record(closure_id)
        closure = record.closure
        events = record.events
        # duration from created_at to last event ts, or 0
        last_ts = closure.created_at
        for ev in events:
            ev_ts = ev.get("ts", 0)
            if isinstance(ev_ts, (int, float)) and ev_ts > last_ts:
                last_ts = ev_ts
        duration = max(0, last_ts - closure.created_at)
        # final_output: last non-empty command_result that isn't a loop-status reason
        loop_keywords = ("Agent Loop", "等待", "需要", "已", "失败", "拒绝", "超限")
        final_output = None
        for cr in reversed(closure.command_results):
            if cr and not any(cr.startswith(k) for k in loop_keywords):
                final_output = cr
                break
        return {
            "closure_id": closure.id,
            "status": closure.status,
            "steps": 0,
            "duration_seconds": round(duration, 1),
            "changed_files": list(closure.changed_files),
            "commands": list(closure.commands),
            "command_results": list(closure.command_results[-5:]),
            "final_output": final_output,
            "error": None,
            "review_summary": closure.review_summary or None,
            "next_action": closure.next_action or None,
            "retry_count": closure.retry_count,
            "permission_requests": list(closure.permission_request_ids),
        }
