import json
from dataclasses import dataclass
from typing import Callable

from bolt_core.context_compressor import ContextCompressor
from bolt_core.conversation import ConversationMessage
from bolt_core.context_builder import ContextBuilder
from bolt_core.model_gateway import DefaultModelGateway, ModelConfig, ModelMessage, ModelRequest, ToolCall
from bolt_core.memory_store import MemoryRecord
from bolt_core.planner import Planner
from bolt_core.tool_operations import operation_for_tool
from bolt_core.tool_protocol import ToolRequest, ToolResult
from bolt_core.trace import TraceLog
from bolt_core.verifier import Verifier
from bolt_core.evidence_redactor import redact


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
    def __init__(self, gateway=None, context_builder=None, planner=None, verifier=None, context_compressor=None) -> None:
        self.gateway = gateway or DefaultModelGateway()
        self.context_builder = context_builder or ContextBuilder()
        self.planner = planner or Planner()
        self.verifier = verifier or Verifier()
        self.context_compressor = context_compressor or ContextCompressor()

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

    def run_loop(self, goal: str, config: ModelConfig, p0_context_fn: Callable[[], dict], trace: TraceLog, submit: Callable[[ToolRequest], ToolResult], memories_fn: Callable[[], list[MemoryRecord]], max_steps: int = 50) -> AgentLoopResult:
        trace.record("agent.loop.started", {"max_steps": max_steps})
        context = self.context_builder.build(goal, p0_context_fn(), trace.events(), memories_fn())
        trace.record("context.built", {"token_budget": context.token_budget, "memory_count": len(context.memory_context)})
        trace.record("planner.started", {})
        initial_request = self.planner.build_request(context, config)
        messages = self._compress_loop_messages(list(initial_request.messages), context.token_budget, trace)
        trace.record("planner.completed", {"messages": len(messages)})
        last_step: AgentStepResult | None = None
        for index in range(max(1, max_steps)):
            trace.record("agent.loop.iteration.started", {"step": index + 1})
            trace.record("llm.requested", {"model": config.model})
            response = self.gateway.complete(ModelRequest(list(messages), config))
            if response.status != "completed":
                trace.record("llm.failed", {"error": response.error})
                last_step = AgentStepResult("failed", response.content or "", None, response.error)
                trace.record("agent.loop.stopped", {"status": "failed", "reason": "llm_failed"})
                return AgentLoopResult("failed", index + 1, last_step, response.error)
            else:
                self._record_model_trace(trace, config.model, response)
                last_step, new_messages = self._dispatch_model_response_with_messages(response, trace, submit)
                messages.extend(new_messages)
                messages = self._compress_loop_messages(messages, context.token_budget, trace)
            trace.record("agent.loop.iteration.completed", {"step": index + 1, "status": last_step.status})
            if last_step.status == "completed" and last_step.tool_result is None:
                trace.record("agent.loop.completed", {"step": index + 1})
                return AgentLoopResult("completed", index + 1, last_step)
            verification = self.verifier.verify(last_step.tool_result)
            if verification.status == "pause_for_permission":
                trace.record("agent.loop.paused", {"status": last_step.status})
                return AgentLoopResult(last_step.status, index + 1, last_step)
            if verification.status == "needs_replan":
                if index + 1 < max(1, max_steps):
                    trace.record("agent.loop.replan_requested", {"status": last_step.status, "reason": verification.reason})
                    continue
                trace.record("agent.loop.replan_exhausted", {"status": last_step.status, "reason": verification.reason})
                return AgentLoopResult("needs_replan", index + 1, last_step, verification.reason)
            if verification.status in ("terminal_failure", "recoverable_failure"):
                trace.record("agent.loop.stopped", {"status": last_step.status, "reason": verification.status})
                return AgentLoopResult(last_step.status, index + 1, last_step, last_step.error)
        trace.record("agent.loop.max_steps_reached", {"steps": max(1, max_steps)})
        return AgentLoopResult(last_step.status if last_step else "failed", max(1, max_steps), last_step)

    def _record_model_trace(self, trace: TraceLog, model: str, response) -> None:
        trace.record("llm.completed", {"model": model})
        trace.record("tokens.recorded", response.usage.__dict__ | {"model": model})

    def _dispatch_model_response(self, response, trace: TraceLog, submit) -> AgentStepResult:
        step, _messages = self._dispatch_model_response_with_messages(response, trace, submit)
        return step

    def _dispatch_model_response_with_messages(self, response, trace: TraceLog, submit) -> tuple[AgentStepResult, list[ModelMessage]]:
        if response.tool_calls:
            history: list[ModelMessage] = [_assistant_tool_call_message(response)]
            last_step: AgentStepResult | None = None
            for call in response.tool_calls:
                last_step = self._submit_tool_call(call, trace, submit)
                if last_step.tool_result is not None:
                    history.append(_tool_result_message(call, last_step.tool_result))
                if last_step.status != "executed":
                    break
            return last_step or AgentStepResult("failed", response.content or "", None, "empty tool call batch"), history
        if response.content:
            trace.record("agent.step.completed", {"status": "completed_text"})
            return AgentStepResult("completed", response.content, None, None), [ModelMessage("assistant", response.content)]
        trace.record("agent.step.failed", {"error": "empty model response"})
        return AgentStepResult("failed", "", None, "empty model response"), []

    def _submit_tool_call(self, call: ToolCall, trace: TraceLog, submit) -> AgentStepResult:
        operation = operation_for_tool(call.name)
        request = ToolRequest.create(call.name, operation, call.arguments)
        result = submit(request)
        trace.record("tool.result.observed", _tool_result_feedback(result))
        verification = self.verifier.verify(result)
        trace.record("verifier.completed", verification.__dict__)
        trace.record("agent.step.completed", {"status": result.status})
        return AgentStepResult(result.status, json.dumps({"tool": call.name, "arguments": call.arguments}), result, None)

    def _compress_loop_messages(self, messages: list[ModelMessage], budget: int, trace: TraceLog) -> list[ModelMessage]:
        plain: list[tuple[int, ModelMessage]] = [
            (index, message) for index, message in enumerate(messages) if _is_plain_text_message(message)
        ]
        if not plain:
            return messages

        compressed = self.context_compressor.compress(
            [ConversationMessage(message.role, message.content, {}) for _, message in plain],
            budget,
        )
        summary = next((m for m in compressed if m.metadata.get("compressed") is True), None)
        recent_plain_count = len([m for m in compressed if not m.metadata.get("compressed")])
        older_plain_count = max(0, len(plain) - recent_plain_count)

        if older_plain_count == 0:
            # Compressor kept every plain message; nothing to replace or drop
            return messages

        older_indexes = {index for index, _ in plain[:older_plain_count]}
        result: list[ModelMessage] = []
        inserted_summary = False
        for index, message in enumerate(messages):
            if index in older_indexes:
                if not inserted_summary and summary is not None:
                    result.append(ModelMessage("user", summary.content))
                    inserted_summary = True
                # Drop older plain messages; if budget is too tight for a summary
                # they are silently removed — still better than full context fallback.
                continue
            result.append(message)
        trace.record("context.compressed", {
            "before": len(messages),
            "after": len(result),
            "compressed_messages": older_plain_count,
            "has_summary": summary is not None,
        })
        return result


def _tool_result_feedback(result: ToolResult) -> dict[str, str | None]:
    output = _safe_feedback_text(result.output)
    error = _safe_feedback_text(result.error)
    return {
        "request_id": result.request_id,
        "status": result.status,
        "reason": _safe_feedback_text(result.reason),
        "output": output,
        "error": error,
    }


def _assistant_tool_call_message(response) -> ModelMessage:
    tool_calls = [{
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.name,
            "arguments": json.dumps(call.arguments),
        },
    } for call in response.tool_calls]
    return ModelMessage("assistant", response.content or "", tool_calls=tool_calls)


def _tool_result_message(call: ToolCall, result: ToolResult) -> ModelMessage:
    return ModelMessage("tool", json.dumps(_tool_result_feedback(result)), tool_call_id=call.id)


def _safe_feedback_text(value: str | None, limit: int = 2000) -> str | None:
    if value is None:
        return None
    text = redact(value)
    return text if len(text) <= limit else text[:limit] + "\n[truncated]"


def _is_plain_text_message(message: ModelMessage) -> bool:
    return message.role in {"user", "assistant"} and not message.tool_call_id and not message.tool_calls
