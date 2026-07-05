# Exec Plan 029 - Agent Product Convergence

## Goal

Consolidate M19-M28 into a single Bolt product roadmap. This is a documentation-only consolidation: it does not start M19, implement business code, change dependencies, add UI, or generate artifacts.

## Inputs

- M19 Real LLM Integration
- M20 Core Tool Expansion
- M21 Vector Memory
- M22 Multi-Agent Delegation
- M23 Multi-Turn Conversation
- M24 Gateway Platform Integration
- M25 Skill System
- M26 Universal Provider System + MoA Mode
- M27 Intelligent Agent Features
- M28 Goal Mode

## Product Thesis

Goal Mode should move forward from a late feature to the long-task control plane. Bolt should first learn to preserve an objective, track evidence, stop safely, and resume. Then tools, providers, skills, memory, subagents, gateways, and advanced intelligence can plug into that durable loop.

## External Product Signals Used

Official docs were checked for current product patterns:

- OpenAI Codex docs: app features, automations, worktrees, browser use, Chrome extension, computer use, commands, AGENTS.md, MCP, hooks, skills, and subagents: https://developers.openai.com/codex/
- OpenAI agent-facing APIs: function calling, web search, MCP/connectors, skills, shell, computer use, apply patch, local shell, conversation state, background mode, compaction, and cost optimization: https://developers.openai.com/codex/
- Claude Code overview: terminal, IDE, desktop, and web surfaces; visual diffs; side-by-side sessions; scheduled tasks; cloud sessions; long-running tasks; and parallel task execution: https://code.claude.com/docs/en/overview
- Claude Code overview: MCP, project instructions and memory, skills, hooks, agent teams, routines, remote control, and channels: https://code.claude.com/docs/en/overview
- Claude Code hooks: lifecycle events around sessions, prompts, tool use, permissions, subagents, tasks, compaction, and file/worktree events: https://code.claude.com/docs/en/hooks
- Claude Code subagents: specialized agents with separate context, tools, and permissions: https://code.claude.com/docs/en/sub-agents

## Reordered Roadmap

| New phase | Pulls from | Product objective |
|---|---|---|
| 1. Execution Core | M19 + M28 foundation | Real tool-calling loop with minimal Goal state |
| 2. Work Tools | M20 + M28 runner | Safe edits, commands, verification, and evidence |
| 3. Conversation Continuity | M23 + M27 auto-compact | Multi-turn state, interruption, compression, persistence |
| 4. Provider Operations | M26 core | Provider registry, fallback, cost, local slash commands |
| 5. Skill Layer | M25 | Reusable task knowledge loaded only when relevant |
| 6. Memory Retrieval | M21 | Semantic memory after useful traces exist |
| 7. Agent Teams | M22 + M27 templates/scopes | Subagents with scoped tools and visible traces |
| 8. Remote Access | M24 | Gateway messaging and safe remote approvals |
| 9. Advanced Intelligence | M26 MoA + M27 remainder | MoA, hooks, checkpoints, multi-repo, automation |

## Phase 1 - Execution Core

**Objective:** Start with M19, but pull forward minimal M28 primitives: `Goal`, criteria, constraints, status, budgets, and evidence log shape.

**Scope:** OpenAI-compatible function calling, structured planner prompt, `ToolCall`, `ModelResponse`, one-tool-call loop, stop states, and a thin goal state model.

**Deferred:** New tools, vector memory, subagents, gateways, MoA, provider registry, and full Goal UI.

**Safety boundary:** Model output never executes directly; PermissionGate remains mandatory; no auto-approve; completion requires recorded evidence.

**Acceptance:** The model can drive one tool call at a time; fake gateway tests use the new response shape; a goal can be represented, started, stopped, and summarized.

## Phase 2 - Work Tools

**Objective:** Execute M20 next, but wire every mutating or long-running tool into Goal evidence and verification.

**Scope:** `file.patch`, `file.write` wiring, `terminal.spawn/poll/kill`, `web.search`, `web.extract`, risk classifications, action evidence, diffs, command output, test output, and files changed.

**Deferred:** Semantic memory, subagent fan-out, provider fallback, remote approvals, and complex budget enforcement.

**Safety boundary:** Writes require diff confirmation; shell and terminal actions require confirmation; web tools stay read-only; background processes are tracked and killable.

**Acceptance:** Bolt can complete a small approved edit, run verification, record evidence, and react differently to a failed command.

## Phase 3 - Conversation Continuity

**Objective:** Execute M23 before memory and delegation so long tasks have durable dialogue, interruption, and recovery.

**Scope:** `ConversationStore`, `ConversationMessage`, history endpoints, mid-loop user message injection, `ContextCompressor`, auto-compact, Goal save/load, unfinished goal discovery, and resume prompts.

**Deferred:** Vector search, subagent spawning, gateways, and full checkpoint manager.

**Safety boundary:** History cannot weaken permissions; compaction preserves hard constraints, criteria, pending approvals, and recent evidence; resume detects workspace drift.

**Acceptance:** A conversation survives restart; a goal resumes with objective, criteria, step count, and evidence; interruptions redirect the next safe step.

## Phase 4 - Provider Operations

**Objective:** Execute M26 core after the durable loop exists: model choice, fallback, cost, and local controls.

**Scope:** Provider registry, environment-resolved keys, multi-provider gateway, fallback for rate limit/timeout/overload, cost tracker, budget checks, and `/model`, `/fallback`, `/providers`, `/status`, `/cost`, `/compact`, `/plan`, `/diff`, `/review`.

**Deferred:** MoA, checkpoint manager, and provider marketplace UI.

**Safety boundary:** API keys are never written to repo files; fallback cannot bypass PermissionGate; cost records stay local; budget exhaustion stops or wraps up the goal.

**Acceptance:** Users can configure and switch providers without code changes; fallback is tested; goal status includes model, cost, and budget.

## Phase 5 - Skill Layer

**Objective:** Execute M25 after conversations and provider controls so skills help durable work instead of becoming static prompt clutter.

**Scope:** `SkillStore`, `SKILL.md` frontmatter, skill matching, max two injected skills, trace visibility, approved skill creation from successful traces, and five seed skills.

**Deferred:** Skill marketplace, automatic self-modification, and subagent-specific skill packs.

**Safety boundary:** Skills are instructions, not executable code; they cannot override safety, permissions, budgets, or goal constraints; skill creation requires approval.

**Acceptance:** Relevant skills load visibly; irrelevant skills stay out; a successful workflow can produce an approval-ready skill draft.

## Phase 6 - Memory Retrieval

**Objective:** Execute M21 after useful conversations, goals, and skill traces exist.

**Scope:** Local embedding service, local vector store, vector-backed `MemoryStore.search`, string fallback, and optional indexing of goal evidence summaries.

**Deferred:** Cloud embeddings, cross-device memory sync, and memory-based auto-approval.

**Safety boundary:** Embeddings are local by default; vector data is local; retrieval is advisory; embedding failure falls back gracefully.

**Acceptance:** Semantic search finds memories by meaning; string fallback works; resolved memories are removed from the vector index.

## Phase 7 - Agent Teams

**Objective:** Execute M22 only after the single-agent Goal loop is reliable.

**Scope:** `SubAgentManager`, delegate tools, max depth 1, max concurrency 3, reviewer/researcher/test-writer/planner/bug-fixer templates, scoped permissions, and parent-visible traces.

**Deferred:** Multi-repo write agents, nested delegation, and autonomous delegation without visible task summaries.

**Safety boundary:** Subagents cannot exceed parent scope; delegation requires confirmation; subagents cannot delegate further; parent goal owns final completion claims.

**Acceptance:** Parent agent can spawn, poll, and consume a subagent result; read-only subagents cannot write or run blocked tools; limits are enforced.

## Phase 8 - Remote Access

**Objective:** Execute M24 after goals, conversations, providers, and permissions are stable.

**Scope:** Gateway adapter interface, Feishu and Telegram adapters, conversation routing, remote permission prompts, rate limiting, gateway status, and later scheduled/thread-like automation.

**Deferred:** Discord, remote auto-approve, public hosted service, and broad organization admin policy.

**Safety boundary:** Gateway is opt-in; credentials stay local and outside the repo; unsupported approval surfaces default to deny; remote users cannot expand workspace scope.

**Acceptance:** A remote message can continue a Bolt conversation; permission can be approved or denied on supported platforms; rate limits are enforced.

## Phase 9 - Advanced Intelligence

**Objective:** Finish deferred M26 and M27 features after the base product is stable.

**Scope:** MoA reference models and aggregator, hook runner, checkpoint manager, conflict-aware resume, multi-repo support, auto-checkpoint before risky operations, and run review.

**Deferred:** Hosted collaboration, marketplace distribution, and organization policy.

**Safety boundary:** Blocking hook failure aborts the step; checkpoints are local with restrictive permissions; MoA respects budget; multi-repo writes require scoped approvals.

**Acceptance:** Checkpoints save and resume with conflict detection; hooks can block unsafe operations; MoA records cost attribution; multi-repo agents stay inside scope.

## Cross-Phase Product Rules

1. Goal Mode is the long-task hub.
2. PermissionGate remains the execution choke point.
3. Completion requires concrete evidence, not model confidence.
4. Provider fallback cannot change tool permissions.
5. Skills and memories are advisory.
6. Subagents and gateways inherit parent scope.
7. Defaults stay local-first: credentials, memory, checkpoints, traces.
8. Add one layer at a time.

## Revised M19-M28 Order

1. M19 Real LLM Integration, with minimal Goal state and evidence primitives from M28.
2. M20 Core Tool Expansion, wired into Goal evidence and verification.
3. M23 Multi-Turn Conversation, plus auto-compact and Goal persistence.
4. M26 Universal Provider System core: registry, fallback, slash commands, cost tracking.
5. M25 Skill System.
6. M21 Vector Memory.
7. M22 Multi-Agent Delegation, plus templates and scoped permissions from M27.
8. M24 Gateway Platform Integration.
9. M28 remaining Goal lifecycle UI and controls.
10. M27 remaining intelligent features and M26 MoA/checkpoint advanced work.

## Out of Scope For M29

- No business code implementation.
- No M19 implementation.
- No dependency changes.
- No provider configuration files.
- No UI components.
- No generated artifacts.

## Verification For This Documentation Change

- `pnpm lint:docs`
- `pnpm quality`

## Acceptance Criteria For M29

- [ ] The M29 roadmap and decision documents exist.
- [ ] `scripts/check-docs.mjs` requires the M19-M29 roadmap docs and M29 decision.
- [ ] The roadmap explicitly reorders M19-M28.
- [ ] Goal Mode is moved forward as the long-task hub.
- [ ] Every phase states objective, scope, deferred items, safety boundary, and acceptance criteria.
- [ ] No business code is changed.
- [ ] `pnpm lint:docs` passes.
- [ ] `pnpm quality` passes.
