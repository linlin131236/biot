import json
from dataclasses import dataclass
from typing import Callable

from bolt_core.context_builder import ContextBuilder
from bolt_core.model_gateway import FakeModelGateway, ModelConfig, ToolCall
from bolt_core.memory_store import MemoryRecord
from bolt_core.planner import Planner
from bolt_core.tool_protocol import ToolRequest, ToolResult
from bolt_core.trace import TraceLog
from bolt_core.verifier import Verifier


@dataclass(frozen=True)
class AgentStepResult:
    status: str
    model_output: str
    tool_result: ToolResult | None
    error: str | None = None


@dataclass(frozen=True)
class AgentLoopResult:
    status: str
    steps: int
    last_step: AgentStepResult | None
    error: str | None = None


class AgentLoop:
    def __init__(self, gateway=None, context_builder=None, planner=None, verifier=None) -> None:
        self.gateway = gateway or FakeModelGateway()
        self.context_builder = context_builder or ContextBuilder()
        self.planner = planner or Planner()
        self.verifier = verifier or Verifier()

    def run_step(self, goal: str, config: ModelConfig, p0_context: dict, trace: TraceLog, submit: Callable[[ToolRequest], ToolResult], memories: list[MemoryRecord] | None = None) -> AgentStepResult:
        context = self.context_builder.build(goal, p0_context, trace.events(), memories)
        trace.record("context.built", {"token_budget": context.token_budget, "memory_count": len(context.memory_context)})
        trace.record("planner.started", {})
        request = self.planner.build_request(context, config)
        trace.record("planner.completed", {"messages": len(request.messages)})
        trace.record("llm.requested", {"model": config.model})
        response = self.gateway.complete(request)
        if response.status != "completed":
            trace.record("llm.failed", {"error": response.error})
            return AgentStepResult("failed", response.content or "", None, response.error)
        self._record_model_trace(trace, config.model, response)
        return self._dispatch_model_response(response, trace, submit)

    def run_loop(self, goal: str, config: ModelConfig, p0_context_fn: Callable[[], dict], trace: TraceLog, submit: Callable[[ToolRequest], ToolResult], memories_fn: Callable[[], list[MemoryRecord]], max_steps: int = 3) -> AgentLoopResult:
        trace.record("agent.loop.started", {"max_steps": max_steps})
        last_step: AgentStepResult | None = None
        for index in range(max(1, max_steps)):
            trace.record("agent.loop.iteration.started", {"step": index + 1})
            last_step = self.run_step(goal, config, p0_context_fn(), trace, submit, memories_fn())
            trace.record("agent.loop.iteration.completed", {"step": index + 1, "status": last_step.status})
            verification = self.verifier.verify(last_step.tool_result)
            if verification.status == "pause_for_permission":
                trace.record("agent.loop.paused", {"status": last_step.status})
                return AgentLoopResult(last_step.status, index + 1, last_step)
            if verification.status in ("terminal_failure", "recoverable_failure", "needs_replan"):
                trace.record("agent.loop.stopped", {"status": last_step.status, "reason": verification.status})
                return AgentLoopResult(last_step.status, index + 1, last_step, last_step.error)
        trace.record("agent.loop.max_steps_reached", {"steps": max(1, max_steps)})
        return AgentLoopResult(last_step.status if last_step else "failed", max(1, max_steps), last_step)

    def _record_model_trace(self, trace: TraceLog, model: str, response) -> None:
        trace.record("llm.completed", {"model": model})
        trace.record("tokens.recorded", response.usage.__dict__ | {"model": model})

    def _dispatch_model_response(self, response, trace: TraceLog, submit) -> AgentStepResult:
        if response.tool_calls:
            call = response.tool_calls[0]
            return self._submit_tool_call(call, trace, submit)
        if response.content:
            trace.record("agent.step.completed", {"status": "completed_text"})
            return AgentStepResult("completed", response.content, None, None)
        trace.record("agent.step.failed", {"error": "empty model response"})
        return AgentStepResult("failed", "", None, "empty model response")

    def _submit_tool_call(self, call: ToolCall, trace: TraceLog, submit) -> AgentStepResult:
        operation = _operation_for_tool(call.name)
        request = ToolRequest.create(call.name, operation, call.arguments)
        result = submit(request)
        verification = self.verifier.verify(result)
        trace.record("verifier.completed", verification.__dict__)
        trace.record("agent.step.completed", {"status": result.status})
        return AgentStepResult(result.status, json.dumps({"tool": call.name, "arguments": call.arguments}), result, None)


def _operation_for_tool(tool_name: str) -> str:
    mapping = {"file.read": "read", "files.search": "search", "file.write": "write", "shell.execute": "command"}
    return mapping.get(tool_name, "read")
