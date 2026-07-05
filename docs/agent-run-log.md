# Bolt Agent Run Log

## Phase 1: Real LLM + Provider Foundation

**Started:** 2026-07-06

**Current Goal:**
Implement real OpenAI-compatible LLM function calling. Replace the current FakeModelGateway-driven JSON text parsing with proper tool_calls. Build ProviderRegistry for multi-provider support. Upgrade Planner prompt. Wire AgentLoop to use tool_calls.

**Existing Code Entry Points:**
- `model_gateway.py`: FakeModelGateway + OpenAICompatibleGateway (urllib, no function calling)
- `agent_loop.py`: _parse_tool_request parses free-form JSON text output
- `planner.py`: One-line system prompt
- `permission_gate.py`: SUPPORTED_OPERATIONS = {file.read, files.search, file.write, shell.execute}
- `harness.py`: Wires AgentLoop with default FakeModelGateway

**Minimal Viable Changes:**
1. Add `openai` SDK to pyproject.toml
2. Create `tool_schemas.py` — OpenAI function specs from SUPPORTED_OPERATIONS
3. Add `ToolCall` dataclass + update `ModelResponse` with `tool_calls`
4. Rewrite `OpenAICompatibleGateway` with openai SDK, function calling, retry, timeout
5. Update `FakeModelGateway` to return tool_calls format
6. Rewrite `Planner` with structured system prompt
7. Rewrite `AgentLoop._submit_model_tool` to use tool_calls
8. Create `provider_registry.py` — ProviderRegistry with env-resolved keys
9. Update `Harness` to use ProviderRegistry

**Success Criteria:**
- FakeModelGateway returns tool_calls, existing tests pass
- OpenAICompatibleGateway sends tools parameter, parses tool_calls
- AgentLoop reads tool_calls from ModelResponse, not free-form JSON
- Planner has structured system prompt with agent identity and rules
- ProviderRegistry resolves providers from env
- All pytest tests pass
- pnpm quality passes
- pnpm --filter @bolt/desktop build passes

**Maximum Risk:**
- Existing tests tightly coupled to free-form JSON parsing — must migrate carefully
- openai SDK install may have dependency conflicts
- ProviderRegistry env resolution needs careful key redaction

**Karpathy Pre-flight:**
Think before coding. The current architecture uses a single `content` string on ModelResponse that contains raw JSON. The new architecture needs `tool_calls: list[ToolCall]` alongside optional `content`. This is a fundamental shape change that touches model_gateway, agent_loop, planner, and tests. Minimal approach: add tool_calls field, keep content for backwards compat, change parsing in agent_loop, update FakeModelGateway to populate both.
