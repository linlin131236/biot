from bolt_core.context_builder import ContextPacket
from bolt_core.model_gateway import ModelConfig, ModelMessage, ModelRequest
from bolt_core.tool_schemas import all_tool_schemas


class Planner:
    def build_request(self, context: ContextPacket, config: ModelConfig) -> ModelRequest:
        system = ModelMessage("system", _system_prompt())
        user = ModelMessage("user", _user_prompt(context))
        return ModelRequest([system, user], config)


def _system_prompt() -> str:
    tools_descriptions = "\n".join(
        f"- {schema['function']['name']}: {schema['function']['description']}"
        for schema in all_tool_schemas()
    )
    return "\n".join([
        "You are Bolt, a desktop coding agent.",
        "",
        "# Your Role",
        "You help the user with coding tasks in their local workspace. You operate through tools only — you cannot act except by issuing tool requests.",
        "",
        "# Available Tools",
        tools_descriptions,
        "",
        "# Rules",
        "1. Read files before editing them. Understand context first.",
        "2. Search the workspace to locate relevant code; do not guess paths.",
        "3. Issue exactly ONE tool request per step. Wait for the result before the next.",
        "4. If a tool fails, read the error, change strategy. Do not repeat the same failing call.",
        "5. Never fabricate file contents, paths, or command output. If you have not seen it via a tool, you do not know it.",
        "6. When the goal is achieved, stop and summarize what you did.",
    ])


def _user_prompt(context: ContextPacket) -> str:
    failures = context.p0_context.get("hard_constraints", [])
    traces = [event.get("type") for event in context.recent_trace]
    tool_results = _tool_result_summaries(context.recent_trace)
    memories = [_memory_summary(memory) for memory in context.memory_context]
    return "\n".join([
        f"Goal: {context.goal}",
        f"Token budget: {context.token_budget}",
        f"Hard constraints: {failures}",
        f"Recent trace: {traces}",
        f"Recent tool results: {tool_results}",
        f"Memories: {memories}",
    ])


def _memory_summary(memory: dict) -> dict:
    summary = {"scope": memory.get("scope"), "tags": memory.get("tags"), "content": memory.get("content")}
    metadata = memory.get("metadata")
    if isinstance(metadata, dict):
        summary["metadata"] = _metadata_summary(metadata)
    return summary


def _tool_result_summaries(events: list[dict]) -> list[dict]:
    results = []
    for event in events:
        if event.get("type") != "tool.result.observed":
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        results.append({
            "status": payload.get("status"),
            "reason": payload.get("reason"),
            "output": payload.get("output"),
            "error": payload.get("error"),
        })
    return results[-5:]


def _metadata_summary(metadata: dict) -> dict:
    keys = ("root_path", "package_manager", "languages", "intent", "scheduler", "truncated")
    return {key: metadata[key] for key in keys if key in metadata}
