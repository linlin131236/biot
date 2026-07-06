"""Task closure recorder for Harness loop results. Records evidence only."""
from bolt_core.agent_loop import AgentLoopResult
from bolt_core.task_closure_service import TaskClosureService
from bolt_core.tool_protocol import ToolResult


class TaskClosureRecorder:
    def __init__(self, service: TaskClosureService | None) -> None:
        self.service = service

    def start_loop(self, run_id: str) -> str | None:
        if self.service is None:
            return None
        closure = self.service.find_by_run(run_id)
        if closure is None:
            return None
        self.service.record_loop_status(closure.id, "loop_started")
        return closure.id

    def record_tool_result(self, closure_id: str, result: ToolResult) -> None:
        if self.service is None:
            return
        self.service.record_tool_result(closure_id, _tool_result_payload(result))

    def record_loop_result(self, closure_id: str | None, result: AgentLoopResult, max_steps: int) -> None:
        if self.service is None or closure_id is None:
            return
        if result.status == "pending_permission" and result.last_step and result.last_step.tool_result:
            self.service.mark_waiting_permission(closure_id, result.last_step.tool_result.request_id)
            return
        if result.status in ("denied", "rejected"):
            self.service.record_loop_status(closure_id, "terminal_failure", result.status)
            return
        if result.status == "failed":
            self.service.record_loop_status(closure_id, "recoverable_failure", result.error or "recoverable_failure")
            return
        if result.steps >= max_steps and max_steps > 0:
            self.service.record_loop_status(closure_id, "max_steps_reached")
            return
        if result.status == "completed":
            self.service.mark_completed(closure_id, "Agent Loop 已完成")
            return
        self.service.record_loop_status(closure_id, result.status)


def _tool_result_payload(result: ToolResult) -> dict:
    return {
        "request_id": result.request_id,
        "status": result.status,
        "reason": result.reason,
        "output": result.output,
        "error": result.error,
    }
