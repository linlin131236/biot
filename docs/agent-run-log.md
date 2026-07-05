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

**Result:**
- Commit: f2a65ee
- 13 files changed, 558 insertions, 91 deletions
- New: tool_schemas.py, provider_registry.py, test_tool_schemas.py, test_provider_registry.py
- Modified: model_gateway.py (ToolCall + tool_calls), agent_loop.py (tool_calls dispatch), planner.py (structured prompt), model_settings.py (timeout)
- All 158 Python tests pass, pnpm quality pass, desktop build pass
- No push
- Risk: openai SDK not tested with real API (no key in env), but FakeModelGateway covers shape

---

## Phase 2: Core Tool Expansion

**Started:** 2026-07-06

**Current Goal:**
Expand core tool set: file.patch, file.write agent loop wiring, shell/test/git tools, terminal spawn/poll/kill, web search/extract. All writes and shell keep PermissionGate. Extend risk classifier and permission gate for new operations.

**Existing Code Entry Points:**
- `tool_schemas.py`: 4 tool schemas (file.read, files.search, file.write, shell.execute)
- `permission_gate.py`: 4 operations
- `risk.py`: classify_command, classify_path
- `tool_executor.py`: ReadOnlyToolExecutor handles 4 tools
- `harness.py`: queues file.write, shell.execute

**Minimal Viable Changes:**
1. Create `background_executor.py` — subprocess spawn/poll/kill
2. Create `web_tools.py` — SearXNG search + urllib extract
3. Extend `tool_schemas.py` — 10 schemas (add file.patch, terminal.spawn/poll/kill, web.search/extract)
4. Extend `permission_gate.py` — new operations (patch, command_bg, web_search, web_extract, test, git)
5. Extend `risk.py` — classify_background_command, classify_search, classify_web, classify_patch
6. Refactor `tool_executor.py` — read-only only, no direct write primitives
7. Update `harness.py` — file.patch changeset flow, terminal execution, web delegation
8. Update `agent_loop.py` — new tool name mapping

**Success Criteria:**
- 10 tool schemas in tool_schemas.py
- file.patch goes through changeset flow (propose → approve → apply)
- terminal.spawn/poll/kill work with BackgroundExecutor
- web.search/extract are auto-allowed
- All writes/shell require PermissionGate
- Architecture check passes (no boundary violations)
- All pytest + pnpm quality + build pass

**Maximum Risk:**
- Architecture boundary check: background_executor uses subprocess, tool_executor imports write primitives
- Need to whitelist background_executor.py as shell execution infrastructure
- Need to keep write primitives in harness.py boundary only

**Result:**
- Commit: 57fe76f
- 19 files changed, 888 insertions, 18 deletions
- New: background_executor.py, web_tools.py, test_background_executor.py, test_web_tools.py, test_file_patch.py
- Modified: tool_schemas.py (10 schemas), permission_gate.py (10 ops), risk.py (6 classifiers), tool_executor.py (read-only), harness.py (patch+terminal+web), agent_loop.py (tool mapping), app.py (new endpoints)
- Updated: check-architecture.mjs (whitelist background_executor.py)
- Updated: protocol.ts (new TypeScript types for all tools)
- 190 Python tests pass, pnpm quality pass, desktop build pass
- No push
- Risk: web_tools.py uses SearXNG public instance (may be rate-limited); background_executor uses subprocess (already whitelisted)

---

## Phase 3: Goal Mode Core

**Started:** 2026-07-06

**Current Goal:**
Add persistent long-running autonomous task control. Goal/GoalBuilder for structured objectives with completion criteria, constraints, budgets. GoalRunner for autonomous loop (plan→act→test→review→iterate). EvidenceLog for immutable audit trail. Lifecycle commands: pause/resume/status/evidence. Budget enforcement: max_steps/max_cost/max_wall_time. Evidence-based completion (not model confidence).

**Existing Code Entry Points:**
- `agent_loop.py`: run_loop with max_steps but no budgets, no evidence, no pause/resume
- `harness.py`: create_run/submit/approve flow
- `model_gateway.py`: FakeModelGateway, OpenAICompatibleGateway with tool_calls

**Minimal Viable Changes:**
1. Create `evidence.py` — Evidence dataclass + EvidenceLog (immutable, append-only)
2. Create `goal.py` — Goal dataclass + GoalBuilder (audit-readiness check)
3. Create `goal_runner.py` — GoalRunner autonomous loop with budget checks, evidence completion, pause/resume
4. Add Goal endpoints to `app.py`
5. Update `harness.py` — integrate GoalRunner

**Success Criteria:**
- GoalBuilder structures vague objectives, rejects unauditable ones
- GoalRunner loops plan/act/test/review/iterate
- Evidence-based completion (must run/cite concrete checks)
- max_steps, max_cost, max_wall_time enforced
- pause/resume/status/evidence API works
- Goal persistence to disk, resume detects file conflicts
- All tests pass, pnpm quality + build pass

**Maximum Risk:**
- GoalRunner loop complexity — keep it thin, delegate to existing AgentLoop
- Evidence-based completion needs careful design to avoid "model confidence = done"
- Persistence format must be simple and robust

**Karpathy Pre-flight:**
Goal Mode is the control plane. The key insight is that GoalRunner should be a thin orchestrator over existing AgentLoop.run_step, not a reimplementation. Each step: check budgets → check completion evidence → plan next action → execute → record evidence → check for self-correction. Evidence is the ground truth; model output is not.
