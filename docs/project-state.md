# Bolt Project State

## 当前稳定基线

- 已完成到：M143 Task Home Cockpit（由本次提交收口，待 push）。
- 最新远端基线：`origin/main = 6977045 feat(M142): add liquid glass component primitives`。
- 当前本地基线：M143 主提交 `47a93bb feat(M143): add task home cockpit`，P1 修复提交收口后待 push。
- 当前本地分支：`main...origin/main`，本地领先远端，待 push。
- 当前工作区：M143 改动已验证，`.claude/` 未跟踪、未提交。
- 未 push / 未 release / 未 tag / 未 delete。

## M143 当前改动

- 首页新增任务驾驶舱。
- 首页显示当前项目、权限边界、运行状态、核心服务。
- 首页新增 6 个安全推荐任务卡片，并修正任务卡片可用性。
- 推荐任务只复用已有 UI 回调，不新增自动执行能力。
- 未选择工作区时，工作区相关任务卡片保持禁用；未创建运行时，轨迹、文档整理、时间线任务保持禁用。
- 继续保持软件产品源码不出现私人称呼。
- 未新增自动批准、push、release、tag、delete 入口。

## M143 关键文件

- `apps/desktop/src/LiquidGlassHome.tsx`
- `apps/desktop/src/LiquidGlassHomeInteraction.test.tsx`
- `apps/desktop/src/liquidGlassHomeInteraction.css`
- `apps/desktop/src/LiquidGlassWorkbench.tsx`
- `docs/superpowers/plans/2026-07-09-m143-task-home-cockpit.md`
- `docs/exec-plans/active/143-task-home-cockpit.md`
- `docs/decisions/143-task-home-cockpit.md`
- `docs/phase-143-review-gate.md`

## M143 验证

- RED：`pnpm --filter @bolt/desktop test -- LiquidGlassHomeInteraction.test.tsx` 失败，原因是首页尚无“任务驾驶舱”和“推荐任务”区域。
- GREEN：`pnpm --filter @bolt/desktop exec vitest run src/LiquidGlassHomeInteraction.test.tsx --reporter verbose`：4 passed。
- P1 修复 targeted：`LiquidGlassHomeInteraction`、`LiquidGlassWorkbench`、`LiquidGlassPrimitives`：12 passed。
- `pnpm --filter @bolt/desktop test`：42 files / 295 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过。
- `uv run pytest -q`：1564 passed，5 warnings。
- 浏览器首页实机检查：通过。
- 产品源码私人称呼扫描：无命中。
- 复审修复：修正待批准权限文案、runId 依赖禁用逻辑和本地/远端基线描述。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M143 改动由本次修复提交收口，待 push。

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
