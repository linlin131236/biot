import json
from dataclasses import dataclass
from typing import Callable

from bolt_core.context_builder import ContextBuilder
from bolt_core.model_gateway import FakeModelGateway, ModelConfig
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
            return AgentStepResult("failed", response.content, None, response.error)
        self._record_model_trace(trace, config.model, response)
        return self._submit_model_tool(response.content, trace, submit)

    def _record_model_trace(self, trace: TraceLog, model: str, response) -> None:
        trace.record("llm.completed", {"model": model})
        trace.record("tokens.recorded", response.usage.__dict__ | {"model": model})

    def _submit_model_tool(self, output: str, trace: TraceLog, submit) -> AgentStepResult:
        parsed = _parse_tool_request(output)
        if isinstance(parsed, str):
            trace.record("agent.step.failed", {"error": parsed})
            return AgentStepResult("failed", output, None, parsed)
        result = submit(parsed)
        verification = self.verifier.verify(result)
        trace.record("verifier.completed", verification.__dict__)
        trace.record("agent.step.completed", {"status": result.status})
        return AgentStepResult(result.status, output, result, None)


def _parse_tool_request(output: str) -> ToolRequest | str:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return "model output is not valid json"
    if not _valid_tool_payload(payload):
        return "model output is not a tool request"
    return ToolRequest.create(payload["tool"], payload["operation"], payload["payload"])


def _valid_tool_payload(payload: dict) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("tool"), str) and isinstance(payload.get("operation"), str) and isinstance(payload.get("payload"), dict)
