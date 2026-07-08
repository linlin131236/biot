# Bolt Project State

## 当前稳定基线

- 已完成到：M140 Harness Execution Lock Boundary（已 push）。
- 最新远端基线：`origin/main = main = caf5493 docs: mark M140 fixes pushed`。
- 当前本地分支：`main...origin/main`，M141 本地验证完成。
- 当前工作区：M141 改动由本次提交收口，`.claude/` 未跟踪、未提交。
- 未 push / 未 release / 未 tag / 未 delete。

## M141 当前修复

- 桌面主界面升级为液态玻璃视觉系统。
- 首页、工作台、设置页统一中文产品文案。
- 深色和浅色主题均支持液态玻璃 token。
- 新增慢速流光边框 `biotBorderFlow`。
- 软件内私人称呼已清理，产品 UI 使用“用户 / 人工批准 / 用户确认”。
- 后端可能被 UI 展示的中文返回文案同步产品化。
- 未新增自动执行、自动批准、push、release、tag、delete 入口。

## M141 关键文件

- `apps/desktop/src/LiquidGlassWorkbench.tsx`
- `apps/desktop/src/LiquidGlassHome.tsx`
- `apps/desktop/src/LiquidGlassSettings.tsx`
- `apps/desktop/src/liquidGlassShell.css`
- `apps/desktop/src/liquidGlassHome.css`
- `apps/desktop/src/liquidGlassSettings.css`
- `apps/desktop/src/LiquidGlassDesignTokens.test.ts`
- `docs/exec-plans/active/141-liquid-glass-visual-system.md`
- `docs/decisions/141-liquid-glass-visual-system.md`
- `docs/phase-141-review-gate.md`

## M141 已完成验证

- Targeted desktop tests：40 files / 287 tests passed。
- Targeted backend tests：137 passed。
- 浏览器实机深色主题检查：通过。
- 浏览器实机浅色主题检查：通过。
- 产品源码私人称呼扫描：无命中。
- `rg "clamp\(" apps/desktop/src -n`：无命中。

## M141 全量验证

- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过，shared 27 passed，desktop 40 files / 287 tests passed。
- `uv run pytest -q`：1564 passed，5 warnings。
- `git diff --check`：通过，仅 Windows LF/CRLF 提示。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M141 改动已验证并由本次提交收口。

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
