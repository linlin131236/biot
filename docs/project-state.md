## 当前稳定基线

- 已完成到：M152 Workspace & Recent Sessions（真实工作区和最近会话），P1/P2 复审修复与安全复审修复均已 push。
- 最新远端基线：`origin/main = bb55e80 docs: mark M152 pushed`。
- 当前本地基线：`HEAD = bb55e80 docs: mark M152 pushed`。
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

## 下一步

- M153 — Permission Center Live：权限中心真实接入。

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
