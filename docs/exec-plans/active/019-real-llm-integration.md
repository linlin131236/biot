# Exec Plan 019 - Real LLM Integration

## Goal

Make Bolt actually usable as a coding agent by replacing FakeModelGateway with a real OpenAI-compatible LLM that supports function calling / tool_use. This is the bridge from "safe skeleton" to "can do real work".

## Why Now

Current state (M8):
- `FakeModelGateway` returns hardcoded fake tool requests based on keyword matching in the prompt.
- `OpenAICompatibleGateway` uses `urllib.request` with no streaming, no function calling, no retry, no error handling, 60s hardcoded timeout.
- `Planner` system prompt is one line: `"Return one JSON tool request with tool, operation, and payload."`
- `AgentLoop._parse_tool_request` expects the model to hand-format JSON. No schema enforcement. Any malformed output = step failure.
- `max_steps=3` hardcoded.

This means Bolt cannot actually solve any real task today. The LLM layer is a placeholder.

## Non-Goals

- No new tools in this plan (that is Plan 020).
- No vector memory (that is Plan 021).
- No multi-agent / delegation (that is Plan 022).
- No conversation history / multi-turn (that is Plan 023).
- No Gateway / messaging platform (that is Plan 024).

This plan ONLY makes the existing 3 tools (file.read, files.search, shell.execute) actually drivable by a real LLM in a reliable loop.

## Scope

### 1. Add `openai` SDK dependency

File: `services/agent-core/pyproject.toml`

```
dependencies = [
  "fastapi>=0.115",
  "pydantic>=2.8",
  "uvicorn>=0.30",
  "openai>=1.50"
]
```

Reinstall venv after change.

### 2. Rewrite `ModelGateway` with function calling

File: `services/agent-core/src/bolt_core/model_gateway.py`

Replace `OpenAICompatibleGateway` with a real implementation:

- Use `openai.OpenAI` client (sync API, matches existing sync code style).
- Use `chat.completions` with `tools` parameter (function calling), NOT free-form JSON text.
- Define tool schemas as OpenAI function specs, generated from `SUPPORTED_OPERATIONS` in `permission_gate.py`.
- Set `tool_choice="auto"`.
- Support streaming optionally (flag, default off for V1).
- Retry with exponential backoff: 3 attempts, 1s/2s/4s, on `APIConnectionError`, `RateLimitError`, `APITimeoutError`.
- Timeout: 120s, configurable via `ModelConfig`.
- Return `ModelResponse` with content (assistant message) AND tool_calls (parsed).
- Keep `FakeModelGateway` for tests, but make it return tool_calls format too.

New dataclass:

```python
@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str       # "file.read" etc
    arguments: dict # parsed JSON args
```

`ModelResponse` gains `tool_calls: list[ToolCall]` field. `content` becomes optional (may be empty when model emits tool calls).

### 3. Define tool schemas centrally

New file: `services/agent-core/src/bolt_core/tool_schemas.py`

Generate OpenAI function specs from the existing `SUPPORTED_OPERATIONS` map. One function per (tool, operation) pair:

```python
FILE_READ_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file.read",
        "description": "Read a file from the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or workspace-relative path"}
            },
            "required": ["path"]
        }
    }
}
# ... files.search, shell.execute, file.write
```

Single source of truth: `permission_gate.SUPPORTED_OPERATIONS` is the authority on what operations exist; `tool_schemas` adds the parameter descriptions the LLM needs.

### 4. Rewrite `Planner` with a real system prompt

File: `services/agent-core/src/bolt_core/planner.py`

Replace the one-line system prompt with a structured prompt:

```
You are Bolt, a desktop coding agent.

# Your Role
You help the user with coding tasks in their local workspace. You operate through tools only — you cannot act except by issuing tool requests.

# Available Tools
{tool list with descriptions, generated from tool_schemas}

# Rules
1. Read files before editing them. Understand context first.
2. Search the workspace to locate relevant code; do not guess paths.
3. Issue exactly ONE tool request per step. Wait for the result before the next.
4. If a tool fails, read the error, change strategy. Do not repeat the same failing call.
5. Never fabricate file contents, paths, or command output. If you have not seen it via a tool, you do not know it.
6. When the goal is achieved, stop and summarize what you did.

# Current Context
Goal: {goal}
Workspace: {workspace_path}
Hard constraints (from past failures): {p0_context.hard_constraints}
Recent trace (last 10 events): {trace_summary}
Relevant memories: {memory_summary}
```

Messages structure:
- `system`: the prompt above
- `user`: the goal (first step) OR the tool result from previous step (subsequent steps)

### 5. Rewrite `AgentLoop` to use tool_calls

File: `services/agent-core/src/bolt_core/agent_loop.py`

Changes:
- `_parse_tool_request` removed. Instead, read `response.tool_calls[0]`.
- `run_step` now takes previous `ToolResult` (or None for first step) and feeds it back as a `tool` role message.
- `run_loop` max_steps default raised to 20 (was 3). Configurable via API.
- Stop conditions:
  1. Model returns no tool_calls (only content) → task done, return summary.
  2. Verification says `terminal_failure` → stop.
  3. Verification says `pause_for_permission` → pause, return.
  4. max_steps reached → stop with status `max_steps_reached`.
- Each step: send context + last tool result → get model response → extract tool_call → submit through harness → get ToolResult → feed back next step.

New method on AgentLoop:

```python
def run_conversation(self, goal, config, p0_context_fn, trace, submit, memories_fn, max_steps=20) -> AgentLoopResult
```

Keeps old `run_step` / `run_loop` as thin wrappers for backward compat with existing tests (or deprecate them — see Verification).

### 6. Update `Harness` wiring

File: `services/agent-core/src/bolt_core/harness.py`

- `run_agent_step` and `run_agent_loop` pass the real gateway (from model_settings) instead of defaulting to FakeModelGateway.
- If model_settings has no API key → return clear error, do not silently use FakeModelGateway.

### 7. Update tests

- All existing tests that used FakeModelGateway must still pass (FakeModelGateway updated to return tool_calls format).
- New tests:
  - `test_real_gateway_builds_tool_calls`: mock `openai.OpenAI`, verify tool_calls parsing.
  - `test_real_gateway_retries_on_rate_limit`: mock retries.
  - `test_real_gateway_timeout`: mock timeout → returns failed response with error.
  - `test_planner_system_prompt_contains_rules`: verify prompt structure.
  - `test_agent_loop_stops_when_no_tool_call`: model returns text only → loop ends with `completed`.
  - `test_agent_loop_feeds_tool_result_back`: verify tool result is included in next request messages.
  - `test_agent_loop_max_steps`: verify loop stops at 20.

## Safety Boundary (unchanged from existing Bolt rules)

- LLM output still never executes directly. Tool calls go through the existing `Harness.submit_tool_request` → `PermissionGate` → `ToolExecutor` chain.
- API key kept in process memory only, never written to repo files, never returned by status endpoints (existing redaction in `model_settings.py` already handles this).
- No new tools added. No new side effects. No network calls except to the configured LLM endpoint.
- `file.write` still requires ChangeSet + user confirmation. `shell.execute` still requires confirmation.

## Verification

Mechanical gates that must pass:

1. `services/agent-core/.venv/Scripts/python -I -m pytest` — all tests pass (existing + new).
2. `pnpm quality` — size, docs, boundary, architecture checks pass.
3. Source files stay under 300 lines (check `model_gateway.py`, `planner.py`, `agent_loop.py` after rewrite).
4. No new dependencies beyond `openai` SDK.

Manual smoke test (documented, not automated):

1. Start Agent Core with a real OpenAI-compatible endpoint configured (e.g. local Ollama, or a real API key).
2. Create a run with goal "Read the README.md in the workspace and tell me what this project is."
3. Verify trace shows: context.built → planner.completed → llm.requested → llm.completed → tool.requested (file.read) → permission.auto_allowed → tool.execution.completed → (next step) llm.requested → llm.completed → no tool_call → loop ends with `completed`.
4. Verify the final `model_output` contains a real summary derived from actual file content, not a fake response.

If the smoke test fails because the model does not return tool_calls, the fallback is NOT to parse free-form JSON. The fix is to use a model that supports function calling. Document supported models in `docs/references/supported-models.md`.

## Out of Scope (explicitly deferred)

| Deferred to | What |
|---|---|
| Plan 020 | More tools: patch, web_search, browser, terminal background |
| Plan 021 | Vector memory (Ollama nomic-embed-text + Qdrant) |
| Plan 022 | Multi-agent / delegate_task |
| Plan 023 | Multi-turn conversation history + context compression |
| Plan 024 | Gateway integration (Feishu / Telegram) |
| Plan 025 | Skill system |

## Acceptance Criteria

- [ ] `openai` SDK added to pyproject.toml, venv reinstalled.
- [ ] `OpenAICompatibleGateway` rewritten with function calling, retry, timeout.
- [ ] `tool_schemas.py` created with schemas for all 4 supported operations.
- [ ] `Planner` system prompt rewritten with real agent identity, rules, context.
- [ ] `AgentLoop` uses tool_calls, feeds results back, max_steps=20, proper stop conditions.
- [ ] All existing tests pass (FakeModelGateway updated).
- [ ] New tests for gateway retry, timeout, loop stop conditions.
- [ ] `pnpm quality` passes.
- [ ] Source files under 300 lines.
- [ ] Manual smoke test documented in `docs/references/m19-smoke-test.md`.
