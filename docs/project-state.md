## 当前稳定基线

- 已完成到：M152 Workspace & Recent Sessions（真实工作区和最近会话），P1/P2 复审修复与安全复审修复均已 push。
- 最新远端基线：`origin/main` 已同步到 M152 pushed 状态（`7f2567b`）。
- 当前本地基线：`HEAD` 在 M152 pushed 状态（`7f2567b`），本地 ahead 5 commits（M153–M157 已 push 到本地但远端未同步）。
  - M153–M156：各有完整 commit（含实现代码、测试、decision、review gate、project-state 更新）。
  - M157：commit `2dd938d` 仅包含 exec plan 文档，实现代码、测试、decision、review gate、project-state 更新均在**工作区未提交**状态。
- 当前本地分支：`main...origin/main [ahead 5]`。
- 当前工作区：M157 实现代码（`TestRunnerPanel.tsx`、`TestRunnerPanel.test.tsx`、`harnessClientAutonomy.ts`、`PanelsSection.tsx`）及 docs（`decision`、`review gate`、`project-state` 更新）均未提交。`.claude/` 未跟踪、未提交。
- 已清理遗留：`docs/exec-plans/active/154-audit-timeline-live.md`（M154 exec plan 不应在工作区遗留）。
- 未 release / 未 tag / 未 delete。
- M153–M157 代码已在工作区就绪，待 M157 commit 后同步远端。

## M151 当前改动

- M151：设置持久化。新增 `desktop_settings.py` + `desktop_settings_api.py`，主题、语言、默认工作区、API 密钥状态可真实读取/保存。API key 不回显明文。
- M151 P1/P2 修复：移除设置页全局 fetch（改用认证回调）、主题切换即时更新 UI、日志脱敏 default_workspace 路径、review gate 文档修正。

## M152 当前改动

- M152：真实工作区和最近会话。新增 `workspace_api.py`，扩展 `desktop_settings.py` 添加 `recent_workspaces` 字段。最近会话来自 `.bolt/goals/goal_*.json` 真实数据。
- 切换工作区后自动添加到最近工作区列表（去重、最多 10 个）。
- 最近会话空状态中文展示：”暂无最近会话”。
- M152 P1/P2 修复：工作区历史由 `App.tsx` 单点写入；最近会话按 goal 文件 mtime 倒序排序；补充 mtime 排序回归测试。

## 安全复审修复

- 本地 API 鉴权：`create_app()` 默认可用于单元测试；模块级生产 `app` 在缺少 `BOLT_AGENT_CORE_TOKEN` 时使用启动失败的占位 app，避免裸奔服务。
- Approval Apply：API 层由服务端注入 `actor=human` 和 proposal scope，不信任请求体自报 actor；保留 forged/auto_generated 拒绝。
- Actor 边界：`approval_apply.py` 与 `tool_permission_contract.py` 只接受 `human` / `用户`，拒绝 `user` / `father` / `agent` 等模糊或私人称呼。
- 新增 `test_approval_apply_api.py`；补充 local auth、approval apply、permission contract 回归测试。

## M152 关键文件

- `services/agent-core/src/bolt_core/workspace_api.py`
- `services/agent-core/src/bolt_core/desktop_settings.py`（新增 recent_workspaces）
- `services/agent-core/src/bolt_core/desktop_settings_api.py`（新增 workspace-history）
- `services/agent-core/src/bolt_core/app.py`（注册 workspace router）
- `apps/desktop/src/harnessClient.ts`（新增 workspace API）
- `apps/desktop/src/workflowClient.ts`（新增 workspace workflow）
- `apps/desktop/src/LiquidGlassWorkbench.tsx`（真实最近会话）
- `apps/desktop/src/App.tsx`（切换工作区后添加历史）
- `apps/desktop/src/LiquidGlassTypes.ts`（新增 props）
- `apps/desktop/src/LiquidGlassWorkbench.test.tsx`（适配新 props）
- `services/agent-core/tests/test_workspace_api.py`
- `docs/exec-plans/active/152-workspace-recent-sessions.md`
- `docs/decisions/152-workspace-recent-sessions.md`
- `docs/phase-152-review-gate.md`

## M152 验证

- Desktop build：通过。
- Desktop tests：42 files / 306 tests passed。
- Backend targeted tests：`test_workspace_api.py` 7 passed，`test_desktop_settings.py` 7 passed。
- 安全 targeted tests：`test_local_api_auth.py`、`test_approval_apply.py`、`test_approval_apply_api.py`、`test_tool_permission_contract.py`、`test_workspace_api.py`、`test_desktop_settings.py` 合计 66 passed。
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- 产品源码私人称呼扫描：无命中。
- renderer 安全扫描：M152 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M152 已完成、已 push。

## M153 当前改动

- M153：权限中心脱敏。`permission_center.py` 的 `payload_summary` 在展示前经过 `evidence_redactor.redact()` 脱敏处理，防止 API key、token、私钥等敏感信息通过权限中心面板泄露。
- 新增 3 个后端脱敏测试（API key inline、TOKEN inline、Bearer）和 1 个前端脱敏展示测试。
- M153 不涉及 PermissionGate 逻辑、approve/reject 流程、前端 UI 改动——所有功能已有 M92 基础设施支撑。

## M153 关键文件

- `services/agent-core/src/bolt_core/permission_center.py`（新增 redact 导入和应用）
- `services/agent-core/tests/test_permission_center.py`（新增 3 个脱敏测试）
- `apps/desktop/src/PermissionCenterPanel.test.tsx`（新增 1 个前端脱敏测试）
- `services/agent-core/src/bolt_core/evidence_redactor.py`（复用已有脱敏工具）

## M153 验证

- Backend targeted tests：17 passed（test_permission_center.py 16 + test_permission_center_api.py 1）
- Frontend targeted tests：11 passed（PermissionCenterPanel.test.tsx）
- Desktop tests：42 files / 310 tests passed（+3 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M153 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。
- 密钥/token 泄露扫描：未命中真实密钥（测试数据仅含假占位符）。

## M154 当前改动

- M154：审计时间线脱敏与类型筛选。`execution_audit_timeline.py` 的 queue item title/reason/result 摘要经过 `evidence_redactor.redact()` 脱敏处理。`/audit-timeline` 端点新增 `source` 查询参数支持按事件来源筛选。前端 `AuditTimelinePanel` 新增类型筛选按钮组（全部/执行队列/人工交接/任务闭环/权限审批）。
- 新增 3 个后端脱敏测试（title/reason/result）、2 个后端 source filter 集成测试、3 个前端筛选/脱敏测试。

## M154 关键文件

- `services/agent-core/src/bolt_core/execution_audit_timeline.py`（新增 redact 应用到 title/reason/result）
- `services/agent-core/src/bolt_core/audit_timeline_api.py`（新增 source 筛选参数）
- `apps/desktop/src/harnessClientAutonomy.ts`（fetchAuditTimeline 新增 source 参数）
- `apps/desktop/src/AuditTimelinePanel.tsx`（新增类型筛选按钮组）
- `services/agent-core/tests/test_execution_audit_timeline.py`（新增 3 个脱敏测试）
- `services/agent-core/tests/test_execution_audit_timeline_api.py`（新增 2 个 source filter 测试）
- `apps/desktop/src/AuditTimelinePanel.test.tsx`（新增 3 个前端测试）

## M154 验证

- Backend targeted tests：11 passed（test_execution_audit_timeline.py 6 + test_execution_audit_timeline_api.py 5）
- Frontend targeted tests：9 passed（AuditTimelinePanel.test.tsx）
- Desktop tests：42 files / 310 tests passed（+3 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M154 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M155 当前改动

- M155：补丁预览中文风险解释与测试补齐。`PatchPreviewPanel.tsx` 新增 `RISK_EXPLANATIONS_CN` 映射，在风险标签旁显示中文风险解释。新建 `test_patch_proposal_api.py` 包含 5 个 patch API 集成测试。`PatchPreviewPanel.test.tsx` 新增 4 个前端测试（风险解释/多文件/空 diff/无执行按钮）。

## M155 关键文件

- `apps/desktop/src/PatchPreviewPanel.tsx`（新增 RISK_EXPLANATIONS_CN）
- `services/agent-core/tests/test_patch_proposal_api.py`（新建，5 个集成测试）
- `apps/desktop/src/PatchPreviewPanel.test.tsx`（新增 4 个前端测试）

## M155 验证

- Backend targeted tests：5 passed（test_patch_proposal_api.py）
- Frontend targeted tests：10 passed（PatchPreviewPanel.test.tsx）
- Desktop tests：42 files / 314 tests passed（+4 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M155 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M155 当前改动

- M155：补丁预览中文风险解释与测试补齐。`PatchPreviewPanel.tsx` 新增 `RISK_EXPLANATIONS_CN` 映射，在风险标签旁显示中文风险解释。新建 `test_patch_proposal_api.py` 包含 5 个 patch API 集成测试。`PatchPreviewPanel.test.tsx` 新增 4 个前端测试。

## M155 关键文件

- `apps/desktop/src/PatchPreviewPanel.tsx`（新增 RISK_EXPLANATIONS_CN）
- `services/agent-core/tests/test_patch_proposal_api.py`（新建，5 个集成测试）
- `apps/desktop/src/PatchPreviewPanel.test.tsx`（新增 4 个前端测试）

## M155 验证

- Backend targeted tests：5 passed（test_patch_proposal_api.py）
- Frontend targeted tests：10 passed（PatchPreviewPanel.test.tsx）
- Desktop tests：42 files / 314 tests passed（+4 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M155 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M156 当前改动

- M156：桌面端批准后应用补丁闭环。`harnessClientAutonomy.ts` 新增 `applyApproval` 函数调用 `/tools/approval/apply` 端点。`harnessClientAutonomy.test.ts` 新增 3 个前端测试。`test_approval_apply_api.py` 新增 2 个后端集成测试（API 注入 approval、过期提案中文错误）。后端 `ApprovalApplyEngine` 已有完整 10 步安全检查链和 19 个测试。

## M156 关键文件

- `apps/desktop/src/harnessClientAutonomy.ts`（新增 applyApproval）
- `apps/desktop/src/harnessClientAutonomy.test.ts`（新增 3 个前端测试）
- `services/agent-core/tests/test_approval_apply_api.py`（新增 2 个集成测试）
- `services/agent-core/src/bolt_core/approval_apply.py`（已有 10 步安全检查链）
- `services/agent-core/src/bolt_core/approval_apply_api.py`（已有 /tools/approval/apply 端点）

## M156 验证

- Backend targeted tests：23 passed（test_approval_apply.py 19 + test_approval_apply_api.py 4）
- Frontend targeted tests：22 passed（harnessClientAutonomy.test.ts）
- Desktop tests：42 files / 317 tests passed（+3 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M156 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M157 当前改动

- M157：安全测试运行器真实接入。新建 `TestRunnerPanel.tsx` 组件，支持白名单测试选择、确认运行、运行中/通过/失败状态展示、脱敏输出和运行历史。`harnessClientAutonomy.ts` 新增 3 个 API 函数（`fetchTestRunnerAvailable`、`runTest`、`fetchTestRunnerHistory`）。`PanelsSection.tsx` 装配 TestRunnerPanel。

## M157 关键文件

- `apps/desktop/src/TestRunnerPanel.tsx`（新建，安全测试运行器面板）
- `apps/desktop/src/TestRunnerPanel.test.tsx`（新建，8 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 3 个 API 函数）
- `apps/desktop/src/PanelsSection.tsx`（装配 TestRunnerPanel）
- `services/agent-core/src/bolt_core/test_runner_integration.py`（已有白名单引擎）
- `services/agent-core/src/bolt_core/test_runner_integration_api.py`（已有 API 端点）

## M157 验证

- Backend targeted tests：7 passed（test_test_runner_integration.py）
- Frontend targeted tests：8 passed（TestRunnerPanel.test.tsx）
- Frontend API tests：22 passed（harnessClientAutonomy.test.ts）
- Desktop tests：43 files / 325 tests passed（+8 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M157 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M158 当前改动

- M158：任务结果总结结构化接入。新建 `TaskResultSummary` 类型（`protocol-closure-summary.ts`）、`TaskResultSummaryBuilder`（`task_closure_result_summary.py`）、`TaskResultSummaryPanel` 组件。`task_closure_api.py` 新增 `GET /task-closures/{id}/result-summary` 端点。`harnessClientAutonomy.ts` 新增 `fetchTaskResultSummary` 函数。`GoalConsole.tsx` 在循环完成后自动加载并展示结果摘要（状态/步数/耗时/变更文件/命令结果/错误/审查摘要/下一步建议）。

## M158 关键文件

- `packages/shared/src/protocol-closure-summary.ts`（新建，TaskResultSummary 接口）
- `services/agent-core/src/bolt_core/task_closure_result_summary.py`（新建，Builder）
- `services/agent-core/src/bolt_core/task_closure_service.py`（新增 result_summary 方法）
- `services/agent-core/src/bolt_core/task_closure_api.py`（新增 endpoint）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 fetchTaskResultSummary）
- `apps/desktop/src/TaskResultSummaryPanel.tsx`（新建，结果摘要面板）
- `apps/desktop/src/GoalConsole.tsx`（装配 TaskResultSummaryPanel）
- `apps/desktop/src/TaskResultSummaryPanel.test.tsx`（新建，5 个前端测试）
- `services/agent-core/tests/test_task_closure_service.py`（新增 3 个 result_summary 测试）

## M158 验证

- Backend targeted tests：3 passed（test_task_closure_service.py result_summary）
- Frontend targeted tests：5 passed（TaskResultSummaryPanel.test.tsx）
- Desktop tests：44 files / 330 tests passed（+5 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M158 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M159 当前改动

- M159：Researcher 执行引擎。新建 `ResearcherEngine`（`researcher_engine.py`）支持按 scope 查询代码地图、决策记忆、失败记忆、项目文档，自动合成原则/风险/source_refs。`researcher_integration_api.py` 新增 `POST /research/execute` 端点。前端新建 `ResearcherPanel` 组件支持创建 brief、执行研究、展示结果。

## M159 关键文件

- `services/agent-core/src/bolt_core/researcher_engine.py`（新建，ResearcherEngine）
- `services/agent-core/src/bolt_core/researcher_integration.py`（保留数据模型）
- `services/agent-core/src/bolt_core/researcher_integration_api.py`（新增 execute 端点）
- `apps/desktop/src/ResearcherPanel.tsx`（新建，研究员面板）
- `apps/desktop/src/ResearcherPanel.test.tsx`（新建，6 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 3 个 API 函数）
- `apps/desktop/src/panelsApi.ts`（新增 researcher namespace）
- `apps/desktop/src/PanelsSection.tsx`（装配 ResearcherPanel）
- `services/agent-core/tests/test_researcher_integration.py`（新增 6 个 execute_brief 测试）

## M159 验证

- Backend targeted tests：6 passed（execute_brief 系列）
- Frontend targeted tests：6 passed（ResearcherPanel.test.tsx）
- Desktop tests：45 files / 336 tests passed（+6 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M159 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M160 当前改动

- M160：Builder 执行引擎。新建 `BuilderEngine`（`builder_engine.py`）根据任务描述产生代码变更提案（FileWriteProposal），不直接写文件。`builder_api.py` 新增 `POST /builder/execute` 端点和 `GET /builder/proposals`。前端新建 `BuilderPanel` 组件支持任务输入、执行、结果展示。

## M160 关键文件

- `services/agent-core/src/bolt_core/builder_engine.py`（新建，BuilderEngine）
- `services/agent-core/src/bolt_core/builder_api.py`（新建，execute + proposals 端点）
- `services/agent-core/src/bolt_core/app.py`（注册 builder router）
- `apps/desktop/src/BuilderPanel.tsx`（新建，构建引擎面板）
- `apps/desktop/src/BuilderPanel.test.tsx`（新建，5 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 2 个 API 函数）
- `apps/desktop/src/panelsApi.ts`（新增 builder namespace）
- `apps/desktop/src/PanelsSection.tsx`（装配 BuilderPanel）
- `services/agent-core/tests/test_builder_engine.py`（新建，6 个后端测试）

## M160 验证

- Backend targeted tests：6 passed（test_builder_engine.py）
- Frontend targeted tests：5 passed（BuilderPanel.test.tsx）
- Desktop tests：46 files / 341 tests passed（+5 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M160 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M161 当前改动

- M161：Reviewer 执行引擎 + strict Gate。新建 `ReviewerEngine`（`reviewer_engine.py`）读取 Builder 输出扫描风险模式（ipcRenderer/process/eval/subprocess 等），strict Gate：P0/P1 → blocked，P2 → changes_requested，无发现 → approved。`reviewer_api.py` 新增 `POST /reviewer/review` 端点。前端新建 `ReviewerPanel` 组件展示 verdict badge + findings 列表。

## M161 关键文件

- `services/agent-core/src/bolt_core/reviewer_engine.py`（新建，ReviewerEngine + strict Gate）
- `services/agent-core/src/bolt_core/reviewer_api.py`（新建，review + verdict 端点）
- `services/agent-core/src/bolt_core/app.py`（注册 reviewer router）
- `apps/desktop/src/ReviewerPanel.tsx`（新建，审查引擎面板）
- `apps/desktop/src/ReviewerPanel.test.tsx`（新建，6 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 2 个 API 函数）
- `apps/desktop/src/panelsApi.ts`（新增 reviewer namespace）
- `apps/desktop/src/PanelsSection.tsx`（装配 ReviewerPanel）
- `services/agent-core/tests/test_reviewer_engine.py`（新建，7 个后端测试）

## M161 验证

- Backend targeted tests：7 passed（test_reviewer_engine.py）
- Frontend targeted tests：6 passed（ReviewerPanel.test.tsx）
- Desktop tests：47 files / 347 tests passed（+6 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M161 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M162 当前改动

- M162：SkillLearner 主动扫描。`skilllearner_review_loop.py` 新增 `auto_scan()` 方法，主动查询 failure memory 检测失败模式并自动生成改进提案。`skilllearner_review_loop_api.py` 新增 `POST /skill-learner/auto-scan` 端点。前端新建 `SkillLearnerPanel` 组件支持自动扫描和提案展示。

## M162 关键文件

- `services/agent-core/src/bolt_core/skilllearner_review_loop.py`（新增 auto_scan 方法）
- `services/agent-core/src/bolt_core/skilllearner_review_loop_api.py`（新增 auto-scan 端点）
- `apps/desktop/src/SkillLearnerPanel.tsx`（新建，技能学习器面板）
- `apps/desktop/src/SkillLearnerPanel.test.tsx`（新建，8 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 autoScanSkillLearner、recordFailure）
- `apps/desktop/src/panelsApi.ts`（新增 skilllearner namespace）
- `apps/desktop/src/PanelsSection.tsx`（装配 SkillLearnerPanel）
- `services/agent-core/tests/test_skilllearner_auto_scan.py`（新建，4 个后端测试）

## M162 验证

- Backend targeted tests：4 passed（test_skilllearner_auto_scan.py）
- Frontend targeted tests：8 passed（SkillLearnerPanel.test.tsx）
- Desktop tests：48 files / 355 tests passed（+8 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M162 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M163 当前改动

- M163：Orchestrator 核心串联 5 角色。新建 `OrchestratorEngine`（`orchestrator_engine.py`）串联 Planner → Researcher → Builder → Reviewer → SkillLearner，支持 review loop（max 3 轮）。`orchestrator_api.py` 新增 `POST /orchestrator/run` 和 `GET /orchestrator/roles` 端点。前端新建 `OrchestratorPanel` 组件展示 5 角色流转和 pipeline trace。

## M163 关键文件

- `services/agent-core/src/bolt_core/orchestrator_engine.py`（新建，OrchestratorEngine）
- `services/agent-core/src/bolt_core/orchestrator_api.py`（新建，run + roles 端点）
- `services/agent-core/src/bolt_core/app.py`（注册 orchestrator router）
- `apps/desktop/src/OrchestratorPanel.tsx`（新建，编排器面板）
- `apps/desktop/src/OrchestratorPanel.test.tsx`（新建，6 个前端测试）
- `apps/desktop/src/harnessClientAutonomy.ts`（新增 2 个 API 函数）
- `apps/desktop/src/panelsApi.ts`（新增 orchestrator namespace）
- `apps/desktop/src/PanelsSection.tsx`（装配 OrchestratorPanel）
- `services/agent-core/tests/test_orchestrator_engine.py`（新建，6 个后端测试）

## M163 验证

- Backend targeted tests：6 passed（test_orchestrator_engine.py）
- Frontend targeted tests：6 passed（OrchestratorPanel.test.tsx）
- Desktop tests：49 files / 361 tests passed（+6 新增测试）
- `pnpm run quality`：通过。
- `git diff --check`：通过。
- Chinese UI check：通过。
- `as any` / `unknown as`：未命中。
- renderer 安全扫描：M163 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## M164 当前改动

- M164：Sleep/Wake 模式。新建 `SleepWakeEngine`（`sleep_wake_engine.py`）管理 Agent 待机/唤醒生命周期，支持 sleep/wake/get_status 操作。`sleep_wake_api.py` 新增 `POST /sleep-wake/sleep`、`POST /sleep-wake/wake`、`GET /sleep-wake/status` 端点。前端新建 `SleepWakePanel` 组件展示状态和操作历史。

## M164 验证

- Backend targeted tests：6 passed（test_sleep_wake_engine.py）
- Frontend targeted tests：6 passed（SleepWakePanel.test.tsx）
- Desktop tests：50 files / 367 tests passed（+6 新增测试）
- `pnpm run quality`：通过。

## 下一步

- **待完成**：commit M164 完整实现（SleepWakeEngine + sleep/wake/status 端点 + SleepWakePanel + 12 测试 + decision + review gate + project-state 更新）。
- M165 — Gate Freeze：生产级 Gate。

## 长期硬规则

- 所有用户可见 UI 必须中文。
- 软件内不使用私人称呼，面向公开产品统一使用”用户 / 人工批准 / 用户确认”。
- 不自动 push、release、tag、delete。
- 不进入未授权 milestone。
- 不绕过 PermissionGate。
- 不自动执行危险命令。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt/`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
