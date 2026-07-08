# Bolt Project State

## 当前稳定基线

- 已完成到：M131 Liquid Glass Desktop Shell（本地完成，等待爸爸复审）。
- 最新远端基线：`origin/main = 16d7e9d fix(P2): stabilize workbench fetch effect`。
- 最新本地提交：以 `git log -1` 为准，本地提交说明为 `feat(M131): add liquid glass desktop shell`。
- 当前本地分支：`main` 基于 `origin/main` 完成 M131 本地改动。
- 未 push / 未 release / 未 tag / 未 delete。
- 未进入 M132。

## 当前状态

- M55-M125 已完成并 push。
- 外部审计硬化已完成并 push。
- M126-M130 Product Workbench 批次已完成并 push。
- M131 新增液态玻璃桌面壳层：
  - 主壳层：`LiquidGlassWorkbench.tsx`。
  - 首页：`LiquidGlassHome.tsx`。
  - 设置中心：`LiquidGlassSettings.tsx`。
  - 类型：`LiquidGlassTypes.ts`。
  - 样式：`liquidGlassShell.css`、`liquidGlassHome.css`、`liquidGlassSettings.css`。
  - 测试：`LiquidGlassWorkbench.test.tsx`。
- 工作区：存在 M131 本地改动；`.claude/` 未跟踪、未提交，按规则保持。

## M131 验证

- `pnpm lint:size`：通过。
- `pnpm --filter @bolt/desktop test`：37 files / 280 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `node scripts/check-chinese-ui.mjs`：通过。
- renderer 暴露扫描：无新增 ipcRenderer / fs / shell / process 暴露。
- 自动执行 / 自动批准 / push-release-tag-delete：无新增入口。

## M131 产出

- `docs/exec-plans/active/131-liquid-glass-desktop-shell.md`
- `docs/decisions/131-liquid-glass-desktop-shell.md`
- `docs/phase-131-review-gate.md`
- `docs/project-state.md`

## 已知风险

- M131 仍保留旧工程面板在折叠区，后续需要继续把权限、补丁、测试、恢复等面板产品化到主工作流。
- `harnessClientAutonomy.ts` 仍是历史豁免的大文件，后续可专项拆分。
- M61 Task Graph / M81-M89 多 Agent 工作流仍以纯内存为主，后续可评估持久化。
- `.claude/` 未跟踪、未提交，按规则保持。

## 下一步建议

- 爸爸复审 M131 液态玻璃桌面壳层。
- 复审通过后可提交 M131。
- 下一步 M132 建议做真实任务输入体验：意图确认、文件范围选择、权限预检和补丁预览前置。

## 长期硬规则

- 所有用户可见 UI 必须中文。
- 不自动 push、release、tag、delete。
- 不进入未授权 milestone。
- 不绕过 PermissionGate。
- 不自动执行危险命令。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
