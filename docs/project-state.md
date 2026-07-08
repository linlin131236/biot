## 当前稳定基线

- 已完成到：M152 Workspace & Recent Sessions（真实工作区和最近会话），P1/P2 复审修复与安全复审修复均已 push。
- 最新远端基线：`origin/main` 已同步到 M152 pushed 状态（具体 hash 以 `git log -1` 为准）。
- 当前本地基线：`HEAD` 已同步到 M152 pushed 状态（具体 hash 以 `git log -1` 为准）。
- 当前本地分支：`main...origin/main`，本地与远端同步。
- 当前工作区：M152 与安全复审修复已完成 targeted/quality 验证，`.claude/` 未跟踪、未提交。
- 未 release / 未 tag / 未 delete。
- 未进入 M153。

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

## 下一步

- M156 — Approval Apply Desktop Flow：桌面端批准后应用补丁闭环。

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
