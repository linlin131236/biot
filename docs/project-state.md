# Bolt Project State

## 当前稳定基线

- 已完成到：M150 Liquid Glass UI Dogfood（本地完成，待复审 / 待 push）。
- 最新远端基线：`origin/main = 61ecee1 docs: mark M143 pushed`。
- 当前本地基线：M150 收口提交（本提交）。
- 当前本地分支：`main...origin/main [ahead 8]`，本地领先远端 8 个提交。
- 当前工作区：M144-M150 改动已完成全量验证，`.claude/` 未跟踪、未提交。
- 未 push / 未 release / 未 tag / 未 delete。

## M144-M150 当前改动

- M144：设置中心产品化，常规、代码预览、模型设置显示独立内容。
- M145：新增权限中心，展示待批准请求、写入门禁、审计记录。
- M146：新增补丁审查页，展示补丁预览、风险摘要、批准写入边界。
- M147：新增审计诊断页，展示审计时间线、诊断中心、恢复建议。
- M148：新增验证发布页，展示验证门禁、测试反馈、发布准备，明确不执行推送、发布或打标签。
- M149：新增智能协作页，展示记忆索引、多 Agent 团队、多任务队列。
- M150：UI dogfood 大复盘，收口文档链和验证清单。

## M144-M150 关键文件

- `apps/desktop/src/LiquidGlassSettings.tsx`
- `apps/desktop/src/LiquidGlassSettingsSurfaces.tsx`
- `apps/desktop/src/LiquidGlassWorkbench.test.tsx`
- `apps/desktop/src/liquidGlassSettings.css`
- `docs/superpowers/plans/2026-07-09-m144-m150-liquid-glass-product-surfaces.md`
- `docs/exec-plans/active/144-settings-productization.md`
- `docs/exec-plans/active/145-permission-center-surface.md`
- `docs/exec-plans/active/146-patch-review-surface.md`
- `docs/exec-plans/active/147-audit-diagnostics-surface.md`
- `docs/exec-plans/active/148-validation-release-surface.md`
- `docs/exec-plans/active/149-memory-team-queue-surface.md`
- `docs/exec-plans/active/150-liquid-glass-ui-dogfood.md`
- `docs/decisions/144-settings-productization.md`
- `docs/decisions/145-permission-center-surface.md`
- `docs/decisions/146-patch-review-surface.md`
- `docs/decisions/147-audit-diagnostics-surface.md`
- `docs/decisions/148-validation-release-surface.md`
- `docs/decisions/149-memory-team-queue-surface.md`
- `docs/decisions/150-liquid-glass-ui-dogfood.md`
- `docs/phase-144-review-gate.md` through `docs/phase-150-review-gate.md`

## M144-M150 验证

- Targeted：`pnpm --filter @bolt/desktop exec vitest run src/LiquidGlassWorkbench.test.tsx --reporter dot`：10 passed。
- Targeted group：`LiquidGlassWorkbench`、`LiquidGlassPrimitives`、`LiquidGlassHomeInteraction`：18 passed。
- Desktop build：通过。
- `pnpm run quality`：通过，shared 27 passed，desktop 42 files / 301 tests passed。
- `uv run pytest -q`：1564 passed，5 warnings。
- `node scripts/check-docs.mjs`：通过。
- `node scripts/check-chinese-ui.mjs`：通过。
- `node scripts/check-size.mjs`：通过。
- `git diff --check`：通过，仅 Windows LF/CRLF 提示。
- 产品源码私人称呼扫描：无命中。
- renderer 安全扫描：本批修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M144-M150 本地完成并通过全量验证，由 M150 收口提交记录。

## 下一步

- 复审后由用户决定是否 push。

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
