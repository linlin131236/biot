# M152 Review Gate - Workspace & Recent Sessions

## 结论

通过。M152 完成了左侧工作区和最近会话从假数据到真实数据源的升级。

## 改动文件

- `services/agent-core/src/bolt_core/desktop_settings.py` — 修改：新增 `recent_workspaces` 字段和 `add_recent_workspace` 方法
- `services/agent-core/src/bolt_core/desktop_settings_api.py` — 修改：新增 `POST /desktop/settings/workspace-history`
- `services/agent-core/src/bolt_core/workspace_api.py` — 新增：workspace API 路由
- `services/agent-core/src/bolt_core/app.py` — 修改：注册 workspace router
- `apps/desktop/src/harnessClient.ts` — 修改：新增 workspace API 调用
- `apps/desktop/src/workflowClient.ts` — 修改：新增 workspace workflow 函数
- `apps/desktop/src/LiquidGlassWorkbench.tsx` — 修改：最近会话从 API 加载，切换工作区后自动添加到最近列表
- `apps/desktop/src/App.tsx` — 修改：切换工作区后调用 `addWorkspaceToHistory`
- `apps/desktop/src/LiquidGlassTypes.ts` — 修改：新增 props
- `apps/desktop/src/LiquidGlassWorkbench.test.tsx` — 修改：适配新 props
- `services/agent-core/tests/test_workspace_api.py` — 新增：后端 targeted tests
- `docs/exec-plans/active/152-workspace-recent-sessions.md` — 新增
- `docs/decisions/152-workspace-recent-sessions.md` — 新增
- `docs/phase-152-review-gate.md` — 新增

## 验证

- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm --filter @bolt/desktop exec vitest run`：42 files / 306 tests passed。
- `pnpm run quality`：通过（size/docs/boundaries/architecture/release/package-runtime/chinese-ui/test）。
- `uv run pytest services/agent-core/tests/test_workspace_api.py services/agent-core/tests/test_desktop_settings.py -q`：13 passed。
- `git diff --check`：通过。

## 安全扫描

- `rg "爸爸|爸" apps/desktop/src`：无命中。
- `rg "as any|unknown as" apps/desktop/src services/agent-core/src`：无命中。
- `rg "ipcRenderer|fs\.|shell\.|process\." apps/desktop/src`：无新增命中。
- `rg "auto approve|自动批准|push|release|tag|delete"`：无新增危险操作。

## 验收

- 切换工作区后 UI 更新（`safeWorkspace` 显示新路径）。
- 最近会话来自真实 backend 数据（`.bolt/goals/goal_*.json`）。
- 空状态中文清晰：未选择工作区时显示"工作区未选择"，无最近会话时显示"暂无最近会话"。
- 不扫描整个磁盘，只读取 `.bolt/goals/` 目录。
- 切换工作区后自动添加到最近工作区列表（去重、最多 10 个）。
- renderer 安全扫描通过。
- `.claude/` 保持未跟踪、未提交。

## 下一步

- 继续 M153 — Permission Center Live。
