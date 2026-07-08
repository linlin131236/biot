# Bolt Project State

## 当前稳定基线

- 已完成到：M151 Settings Persistence（真实设置持久化），已 commit 未 push。
- 最新远端基线：`origin/main = 51e2502 docs: mark M150 pushed`。
- 当前本地基线：`HEAD = 3ad65c0 feat(M151): real settings persistence for desktop`。
- 当前本地分支：`main...origin/main [ahead 1]`，本地领先远端 1 个 commit（M151）。
- 当前工作区：M151 改动已完成全量验证，`.claude/` 未跟踪、未提交。
- 未 release / 未 tag / 未 delete。
- 未进入 M152。

## M151 当前改动

- M151：设置持久化。新增 `desktop_settings.py` + `desktop_settings_api.py`，主题、语言、默认工作区、API 密钥状态可真实读取/保存。API key 不回显明文。

## M151 关键文件

- `services/agent-core/src/bolt_core/desktop_settings.py`
- `services/agent-core/src/bolt_core/desktop_settings_api.py`
- `services/agent-core/src/bolt_core/app.py`（新增路由注册）
- `apps/desktop/src/harnessClient.ts`（新增 desktop settings API）
- `apps/desktop/src/workflowClient.ts`（新增 desktop settings workflow）
- `apps/desktop/src/App.tsx`（settings state 提升，主题持久化）
- `apps/desktop/src/LiquidGlassTypes.ts`（新增 props）
- `apps/desktop/src/LiquidGlassWorkbench.tsx`（主题切换持久化）
- `apps/desktop/src/LiquidGlassSettings.tsx`（真实数据展示）
- `apps/desktop/src/LiquidGlassSettingsData.tsx`（静态 surface 数据拆分）
- `apps/desktop/src/LiquidGlassWorkbench.test.tsx`（适配新 props）
- `services/agent-core/tests/test_desktop_settings.py`
- `docs/exec-plans/active/151-settings-persistence.md`
- `docs/decisions/151-settings-persistence.md`
- `docs/phase-151-review-gate.md`

## M151 验证

- Desktop build：通过。
- Desktop tests：42 files / 305 tests passed。
- Backend targeted tests：`test_desktop_settings.py` 7 passed，`test_model_settings.py` + `test_app.py` 26 passed。
- `pnpm run quality`：通过（size/docs/boundaries/architecture/release/package-runtime/chinese-ui/test）。
- `git diff --check`：通过。
- 产品源码私人称呼扫描：无命中。
- renderer 安全扫描：M151 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。
- `desktop_settings.py` 写文件已加入 `check-architecture.mjs` 白名单。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M151 已完成、已复审，待 commit。未 push。

## 下一步

- M151 复审 FAIL，修复 P1/P2 后重新复审。不进入 M152。

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
