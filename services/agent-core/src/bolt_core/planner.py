from bolt_core.context_builder import ContextPacket
from bolt_core.model_gateway import ModelConfig, ModelMessage, ModelRequest


class Planner:
    def build_request(self, context: ContextPacket, config: ModelConfig) -> ModelRequest:
        system = ModelMessage("system", "Return one JSON tool request with tool, operation, and payload.")
        user = ModelMessage("user", _prompt(context))
        return ModelRequest([system, user], config)


def _prompt(context: ContextPacket) -> str:
    failures = context.p0_context.get("hard_constraints", [])
    memories = [memory["content"] for memory in context.memory_context]
    return f"Goal: {context.goal}\nToken budget: {context.token_budget}\nHard constraints: {failures}\nMemories: {memories}"
