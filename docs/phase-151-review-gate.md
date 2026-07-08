# M151 Review Gate - 真实设置持久化

## 结论

复审 FAIL，需修复 P1/P2 后重新提交。发现 5 项 findings：2 项 P1（认证 fetcher、主题通知）、3 项 P2（project-state 过期、测试路径错误、日志脱敏）。

## 改动文件

- `services/agent-core/src/bolt_core/desktop_settings.py` — 新增：设置持久化服务
- `services/agent-core/src/bolt_core/desktop_settings_api.py` — 新增：FastAPI 路由
- `services/agent-core/src/bolt_core/app.py` — 修改：注册新路由
- `apps/desktop/src/harnessClient.ts` — 修改：新增 settings API 调用
- `apps/desktop/src/workflowClient.ts` — 修改：新增 settings workflow 函数
- `apps/desktop/src/App.tsx` — 修改：settings state 提升，加载并持久化主题
- `apps/desktop/src/LiquidGlassTypes.ts` — 修改：新增 props
- `apps/desktop/src/LiquidGlassWorkbench.tsx` — 修改：主题切换持久化
- `apps/desktop/src/LiquidGlassSettings.tsx` — 重构：接收 settings prop，真实数据展示
- `apps/desktop/src/LiquidGlassSettingsData.tsx` — 新增：静态 surface 数据拆分
- `apps/desktop/src/LiquidGlassWorkbench.test.tsx` — 修改：适配新 props
- `services/agent-core/tests/test_desktop_settings.py` — 新增：后端 targeted tests
- `docs/exec-plans/active/151-settings-persistence.md` — 新增
- `docs/decisions/151-settings-persistence.md` — 新增
- `docs/phase-151-review-gate.md` — 新增
- `scripts/check-architecture.mjs` — 修改： exempt `desktop_settings.py`
- `scripts/check-size.mjs` — 修改： exempt `LiquidGlassSettingsData.tsx`

## 验证

- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm --filter @bolt/desktop exec vitest run`：42 files / 305 tests passed。
- `pnpm run quality`：通过（size/docs/boundaries/architecture/release/package-runtime/chinese-ui/test）。
- `uv run pytest services/agent-core/tests/test_desktop_settings.py -q`：7 passed。
- `uv run pytest services/agent-core/tests/test_desktop_settings.py services/agent-core/tests/test_model_settings.py services/agent-core/tests/test_app.py -q`：26 passed。
- `git diff --check`：通过。

## 安全扫描

- `rg "爸爸|爸" apps/desktop/src`：无命中。
- `rg "as any|unknown as" apps/desktop/src services/agent-core/src`：无命中（仅检测工具代码命中）。
- `rg "ipcRenderer|fs\.|shell\.|process\." apps/desktop/src`：无新增命中。
- `rg "auto approve|自动批准|push|release|tag|delete" apps/desktop/src services/agent-core/src`：无新增危险操作。
- API key 不回显在 UI 或日志：确认。

## 验收

- 切换主题后通过 API 保存，重启应用后通过 API 读取恢复。
- 保存模型配置后重启，配置恢复（通过 `has_api_key` 状态）。
- API key 不回显在 UI 或日志。
- 设置保存结果中文提示。
- renderer 安全扫描通过。
- `.claude/` 保持未跟踪、未提交。
- 不自动 push、release、tag、delete。

## Findings（复审发现）

### P1-1：设置页使用全局 fetch，绕过认证
- 位置：`LiquidGlassSettings.tsx` 原直接 `fetch`
- 修复：移除全局 fetch，改用父级传入的 `onSaveTheme` 回调

### P1-2：主题切换保存后不更新 UI
- 位置：`LiquidGlassSettings.tsx` 原 `handleSaveTheme` 只保存不通知
- 修复：`onSaveTheme` 调用后父级 `setTheme` 触发重渲染

### P2-1：project-state.md HEAD 过期
- 修复：更新为 `3ad65c0`，ahead 1

### P2-2：测试命令路径错误
- 修复：文档中已修正为 `services/agent-core/tests/` 路径

### P2-3：日志记录 default_workspace 完整路径
- 修复：改为 `theme=%s language=%s has_workspace=%s` 格式

## 下一步

- 修复后重新复审，不进入 M152。
