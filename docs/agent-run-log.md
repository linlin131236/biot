# Bolt Agent Run Log

## Phase 1: Real LLM + Provider Foundation

**Started:** 2026-07-06
**Commit:** f2a65ee

**Changes:**
- tool_schemas.py: 4 OpenAI function specs (file.read, files.search, file.write, shell.execute)
- model_gateway.py: ToolCall dataclass + OpenAICompatibleGateway with tool_calls
- agent_loop.py: tool_calls 替代自由格式 JSON
- planner.py: 结构化系统提示词
- provider_registry.py: BUILTIN_PROVIDERS
- model_settings.py: timeout
- pyproject.toml: openai>=1.50

**Tests:** 158/158 pass
**Verification:** pnpm quality + build pass

---

## Phase 2: Core Coding Tools

**Started:** 2026-07-06
**Commit:** 57fe76f

**Changes:**
- background_executor.py: 后台进程管理
- web_tools.py: web 搜索/提取
- permission_gate.py: 10 个操作
- risk.py: 风险分类器
- tool_schemas.py: 10 个 schemas
- tool_executor.py: ReadOnlyToolExecutor
- harness.py: terminal/web 工具直接处理
- app.py: 新端点

**Tests:** 190/190 pass
**Verification:** pnpm quality + build pass

---

## Phase 3: Persistent Goal Mode

**Started:** 2026-07-06
**Commit:** 5cc269c

**Changes:**
- evidence.py: Evidence frozen dataclass + EvidenceLog
- goal.py: Goal, GoalBuilder, GoalStatus
- goal_runner.py: GoalRunner + GoalRunnerResult
- goal_service.py: GoalService + GoalPersistence
- app.py: 8 个 Goal API 端点
- harness.py: goal_service 组合

**Tests:** 213/213 pass
**Verification:** pnpm quality + build pass

---

## Phase 1-3 Review Gate

**Date:** 2026-07-06

**4 Red Risks Found:**
1. BackgroundExecutor stdout 管道死锁
2. goal_id 路径遍历漏洞
3. GoalRunner 默认 evidence_type 完成判定太宽松
4. harness.py 仅 5 行余量

**Report:** docs/phase-1-3-review-gate.md

---

## Phase 0: Review Gate Fix

**Started:** 2026-07-06
**Commit:** 3796bcc

**Changes:**
- background_executor.py: 后台线程持续消费 stdout，max_output_size=1MB，completed 后释放引用
- goal_persistence.py: 拆分自 goal.py，goal_id 正则验证，原子写入 (temp+rename)，损坏 JSON 异常
- goal.py: 移除 GoalPersistence，不再需要 write 白名单
- goal_runner.py: 移除默认 evidence_type 自动完成，加 consecutive_failures (3次→FAILED)，默认 min cost 0.01
- terminal_service.py: 拆分自 harness.py
- harness.py: 295→271 行，使用 TerminalService + ConversationStore
- check-architecture.mjs: goal.py 出白名单，goal_persistence.py 入白名单

**Tests:** 230/230 pass
**Verification:** pnpm quality + build pass

---

## Phase 4: Multi-turn Conversation + Side Chat

**Started:** 2026-07-06
**Commit:** 07e783c

**Changes:**
- conversation.py: ConversationStore (SQLite), ConversationMessage
- context_compressor.py: 保留 system/权限/失败证据，压缩旧消息
- app.py: 6 个新端点 (conversations, messages, steering, timeline)
- harness.py: conversation_store 组合

**Tests:** 242/242 pass
**Verification:** pnpm quality + build pass

---

## Phase 5: Vector Memory

**Started:** 2026-07-06
**Commit:** 7ad455d

**Changes:**
- vector_memory.py: LocalHashEmbedding (确定性 fallback), VectorMemoryStore (record/search/delete), secret pattern 拒绝

**Tests:** 251/251 pass
**Verification:** pnpm quality + build pass

---

## Phase 6: Skill System

**Started:** 2026-07-06
**Commit:** 1cd96bc

**Changes:**
- skill.py: SkillManifest (SKILL.md 解析), SkillStore (加载/匹配/路径遍历防护), SkillSelector, bypass_permission 拒绝

**Tests:** 259/259 pass
**Verification:** pnpm quality + build pass

---

## Phase 7: Multi-agent Delegation

**Started:** 2026-07-06
**Commit:** 3e00a7f

**Changes:**
- delegation.py: AgentRole, DelegationTask 生命周期, reviewer fail→needs_revision, evidence 必填

**Tests:** 267/267 pass
**Verification:** pnpm quality + build pass

---

## Phase 8: Provider Policy + MoA

**Started:** 2026-07-06
**Commit:** 9af4c72

**Changes:**
- provider_policy.py: ProviderCapability 路由, ProviderPolicy (tier/cost)
- moa.py: MoAOrchestrator (dry_run 默认), secret scrubbing, budget enforce, dissent 记录

**Tests:** 274/274 pass
**Verification:** pnpm quality + build pass

---

## Phase 9: Checkpoints + Review Gate

**Started:** 2026-07-06
**Commit:** 1072c6c

**Changes:**
- checkpoint.py: CheckpointService (快照/恢复/不含大文件/不含 secrets), no subprocess (delegated)
- review_gate.py: ReviewGate + ReviewChecklist + ReviewResult
- check-architecture.mjs: checkpoint.py 入白名单 (元数据持久化基础设施)

**Tests:** 283/283 pass
**Verification:** pnpm quality + build pass

---

## Desktop Integration

**Started:** 2026-07-06
**Commit:** 42f0aa9

**Changes:**
- protocol-autonomy.ts: 99 行，Goal/Conversation/VectorMemory/Skill/Delegation/MoA/Checkpoint/Review 类型
- harnessClientAutonomy.ts: 18 个新 API 方法
- packages/shared/package.json: 加 "./autonomy" export

**Verification:** 283 pytest + pnpm quality + desktop build pass

---

## M31 Integration Smoke

**Started:** 2026-07-06

**Changes:**
- app.py: checkpoint and review gate routes wired to existing services
- harnessClientAutonomy.ts: checkpoint and review methods call real endpoints
- test_integration_smoke.py: run/goal/conversation/tool/permission/checkpoint/review/loop/timeline smoke
- harnessClientAutonomy.test.ts: desktop client route contract coverage

**Verification:** 287 pytest + pnpm quality (11 shared, 53 desktop) + desktop build pass

---

## M32 Desktop Dogfood Smoke

**Started:** 2026-07-06

**Changes:**
- test_dogfood_smoke.py: backend dogfood path (run→goal→conv→read→patch→approve→checkpoint→review→timeline)
- test_dogfood_smoke.py: reject permission does not modify file
- test_dogfood_smoke.py: unwired surfaces return 404
- dogfoodSmoke.test.ts: desktop client dogfood path + unwired surface explicit throw
- workflowClient.ts: added goal/conversation/checkpoint/review/timeline/tool helpers
- App.tsx: added Create Goal, Timeline, Review buttons; Dogfood panel; fixed corrupted labels
- App.test.tsx: updated button/label selectors to match fixed Chinese text
- check-docs.mjs: added M32 docs to quality gate
- 032 exec plan + decision docs

**Verification:** 290 pytest + 55 vitest + pnpm quality + desktop build pass

---

## M33 UI Workflow Dogfood + Chinese Desktop Experience

**Started:** 2026-07-06

**Changes:**
- App.tsx: all user-visible text changed to Chinese; added ToolFlowPanel (file path/read/patch inputs)
- App.test.tsx: all button/label selectors updated to Chinese
- uiWorkflowDogfood.test.tsx: 10 new tests — Chinese UI assertions + click path + tool flow
- harnessClient import: added submitToolRequest for tool flow
- 033 exec plan + decision docs
- check-docs.mjs: added M33 docs to quality gate

**Verification:** 290 pytest + 65 vitest + pnpm quality + desktop build pass

---

## M34 Chinese Desktop Quality

**Started:** 2026-07-06

**Changes:**
- scripts/check-chinese-ui.mjs: mojibake + tool-protocol quality gate
- package.json: added lint:chinese-ui to quality pipeline
- uiWorkflowDogfood.test.tsx: fixed mock tool "file" → "file.patch"
- 034 exec plan + decision docs
- check-docs.mjs: added M34 docs to quality gate

**Verification:** 290 pytest + vitest + pnpm quality (incl. lint:chinese-ui) + desktop build pass

---

## M35 Real Workspace File Picker + Safe Workspace Binding

**Started:** 2026-07-06

**Changes:**
- risk.py: _is_inside_workspace uses relative_to (fixes sibling prefix)
- path_guard.py: check resolves relative paths against workspace (ws / target)
- harness.py: _queue_file_patch uses PathGuard instead of raw _is_inside_workspace
- App.tsx: selectWorkspace adapter, changeWorkspace action, 更换工作区/选择工作区 button, 工作区未选择 display, hasWorkspace guard, relative path placeholder
- uiWorkflowDogfood.test.tsx: 4 M35 workspace binding tests
- test_workspace_binding.py: 9 pytest tests (relative, traversal, sibling, secret)
- 035 exec plan + decision docs
- check-docs.mjs: added M35 docs

**Verification:** 299 pytest + 25 vitest + pnpm quality + desktop build pass

---

## M36 Native Workspace Picker + Electron Security Bridge

**Started:** 2026-07-06

**Changes:**
- electron/workspacePicker.ts: extracted handler + registerWorkspacePickerIpc (bolt:select-workspace, openDirectory only)
- electron/preload.ts: contextBridge.exposeInMainWorld('bolt', { selectWorkspace }) — no raw ipcRenderer
- electron/main.ts: registerWorkspacePickerIpc(ipcMain, dialog) on app.whenReady
- src/App.tsx: defaultSelectWorkspace uses window.bolt?.selectWorkspace, fallback Chinese prompt
- src/global.d.ts: Window.bolt type declaration
- workspacePicker.test.ts: 5 tests (success, cancel, openDirectory, empty paths, channel name)
- preloadBridge.test.ts: 4 tests (invoke, cancel, no ipcRenderer, no generic invoke)
- mainSecurity.test.ts: 7 tests (contextIsolation, nodeIntegration, preload.js, no remote, registerWorkspacePickerIpc, channel, openDirectory)
- uiWorkflowDogfood.test.tsx: +3 tests (cancel preserves workspace, window.bolt reference, workspace button)
- 036 exec plan + decision docs
- check-docs.mjs: added M36 docs

**Verification:** 299 pytest + 88 vitest + pnpm quality + desktop build pass
