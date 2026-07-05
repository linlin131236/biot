from bolt_core.context_builder import ContextPacket
from bolt_core.model_gateway import ModelConfig, ModelMessage, ModelRequest


class Planner:
    def build_request(self, context: ContextPacket, config: ModelConfig) -> ModelRequest:
        system = ModelMessage("system", "Return one JSON tool request with tool, operation, and payload.")
        user = ModelMessage("user", _prompt(context))
        return ModelRequest([system, user], config)


def _prompt(context: ContextPacket) -> str:
    failures = context.p0_context.get("hard_constraints", [])
    traces = [event.get("type") for event in context.recent_trace]
    memories = [_memory_summary(memory) for memory in context.memory_context]
    return "\n".join([
        f"Goal: {context.goal}",
        f"Token budget: {context.token_budget}",
        f"Hard constraints: {failures}",
        f"Recent trace: {traces}",
        f"Memories: {memories}",
    ])


def _memory_summary(memory: dict) -> dict:
    summary = {"scope": memory.get("scope"), "tags": memory.get("tags"), "content": memory.get("content")}
    metadata = memory.get("metadata")
    if isinstance(metadata, dict):
        summary["metadata"] = _metadata_summary(metadata)
    return summary


def _metadata_summary(metadata: dict) -> dict:
    keys = ("root_path", "package_manager", "languages", "intent", "scheduler", "truncated")
    return {key: metadata[key] for key in keys if key in metadata}
