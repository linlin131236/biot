# Bolt Project State

## 当前稳定基线

- 已完成到：M141 Liquid Glass Visual System（已 push）。
- 最新远端基线：`origin/main = main = e1aaf2e feat(M141): polish liquid glass desktop experience`。
- 当前本地分支：`main...origin/main`，M142 本地验证完成。
- 当前工作区：M142 改动由本次提交收口，`.claude/` 未跟踪、未提交。
- 未 push / 未 release / 未 tag / 未 delete。

## M142 当前修复

- 新增 Liquid Glass primitives 组件层。
- 新增 `GlassButton`、`GlassPanel`、`GlassPill`、`GlassToolbar`。
- 新增 primitives CSS，统一按钮、面板、pill、toolbar 的玻璃质感。
- 首页任务 composer 和快捷操作开始接入 primitives。
- 设置页 tabs、面板和部分操作按钮开始接入 primitives。
- 继续保持软件产品源码不出现私人称呼。
- 未新增自动执行、自动批准、push、release、tag、delete 入口。

## M142 关键文件

- `apps/desktop/src/LiquidGlassPrimitives.tsx`
- `apps/desktop/src/LiquidGlassPrimitives.test.tsx`
- `apps/desktop/src/liquidGlassPrimitives.css`
- `apps/desktop/src/LiquidGlassHome.tsx`
- `apps/desktop/src/LiquidGlassSettings.tsx`
- `apps/desktop/src/LiquidGlassWorkbench.tsx`
- `docs/exec-plans/active/142-liquid-glass-component-system.md`
- `docs/decisions/142-liquid-glass-component-system.md`
- `docs/phase-142-review-gate.md`

## M142 已完成验证

- RED：`pnpm --filter @bolt/desktop test -- LiquidGlassPrimitives.test.tsx` 失败，原因是 `LiquidGlassPrimitives` 尚不存在。
- GREEN：`pnpm --filter @bolt/desktop test -- LiquidGlassPrimitives.test.tsx LiquidGlassWorkbench.test.tsx LiquidGlassDesignTokens.test.ts`：41 files / 290 tests passed。
- `node scripts/check-size.mjs`：通过。
- 产品源码私人称呼扫描：无命中。

## M142 待完成验证

无。

## M142 全量验证

- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过，shared 27 passed，desktop 41 files / 290 tests passed。
- `uv run pytest -q`：1564 passed，5 warnings。
- `git diff --check`：通过，仅 Windows LF/CRLF 提示。
- 浏览器首页实机检查：通过。
- 浏览器设置页实机检查：通过。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M142 改动已验证并由本次提交收口。

## 下一步

- 等待复审，不自动 push。

## 长期硬规则

- 所有用户可见 UI 必须中文。
- 软件内不使用私人称呼，面向公开产品统一使用“用户 / 人工批准 / 用户确认”。
- 不自动 push、release、tag、delete。
- 不进入未授权 milestone。
- 不绕过 PermissionGate。
- 不自动执行危险命令。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
