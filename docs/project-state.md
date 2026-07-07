# Bolt Project State

## 当前稳定基线
- 已完成到：M100 桌面 Beta Dogfood（V5 终点，等待爸爸复审）
- V5 中文产品 UI/UX（M91-M100）已完成并进入复审修复收口。
- 远程状态：M91-M100 本地完成，**未 push / 未 release / 未 tag / 未 delete**。
- 当前本地分支：`main` ahead `origin/main`，以 `git status --short --branch` 为准。
- 最近稳定链路：M61 -> M90 -> M91 -> M92 -> M93 -> M94 -> M95 -> M96 -> M97 -> M98 -> M99 -> M100。

## 当前进行中
- 当前阶段：**M100 复审修复已完成并通过验证，未进入 M101**。
- 本次修复项：
  - 修复 `SettingsToolsPanel.test.tsx` 文本匹配导致的桌面测试失败。
  - 将 `DesktopBetaDogfoodService` 从硬编码全通过改为真实检查文件、路由、逐 M 文档链、中文 UI、安全边界和未进入 M101。
  - 补齐 M93-M100 独立 exec plan / decision / phase review gate 文档链。
  - 修正 `check-size.mjs` 豁免注释，明确超限文件是已记录的临时风险。
  - 清理本文件中过期的测试数字和重复风险段。
- 当前状态：未 push / 未 release / 未 tag / 未 delete / 未进入 M101。

## V5 里程碑结果
- M91：中文任务首页。
- M92：权限中心。
- M93：审计时间线视图。
- M94：诊断中心。
- M95：发布准备页。
- M96：多任务队列。
- M97：失败解释体验。
- M98：会话恢复体验。
- M99：设置/模型/工具面板。
- M100：桌面 Beta Dogfood 大复盘。

## 最新验证记录
- `pnpm --filter @bolt/desktop test -- SettingsToolsPanel.test.tsx`：实际运行 desktop 全套，**34 files / 262 tests passed**。
- `uv run pytest -q services/agent-core/tests/test_desktop_beta_dogfood.py`：**5 passed**。
- `pnpm --filter @bolt/desktop test`：**34 files / 262 tests passed**。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm --filter @bolt/shared test`：**27 passed**。
- `pnpm run quality`：通过。
- `uv run pytest -q --color=no`（在 `services/agent-core`）：**1225 passed, 1 warning**。
- 当前全量测试基线：**1225 backend + 27 shared + 262 desktop = 1514 passed**。
- `git diff --check`：通过，仅 Windows LF/CRLF 提示。
- `node scripts/check-docs.mjs`：通过。
- `node scripts/check-chinese-ui.mjs`：通过。

## 已知风险
- 部分历史文件超过 300 行，已在 `scripts/check-size.mjs` 作为临时豁免记录；后续应专项拆分。
- `apps/desktop/src/harnessClientAutonomy.ts` 超过 300 行，是 M79-M99 客户端函数累积结果，已记录为临时豁免，不应继续扩张。
- M61 Task Graph 与 M81-M89 多 Agent 工作流仍以纯内存为主，服务重启后状态可能丢失；后续持久化需另立 milestone。
- `.claude/` 未跟踪、未提交，按规则保持。

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
- 代码文件尽量保持在 300 行以内，接近上限时拆到聚焦组件或服务。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。

## 新窗口接手指令
```text
工作目录：D:\Bolt\Bolt

请先恢复项目上下文，不要改文件：
1. 读取 docs/project-state.md
2. 读取最新 docs/phase-*-review-gate.md
3. 运行 git status --short --branch
4. 运行 git log --oneline -10 --decorate
5. 汇报当前稳定基线、最新本地提交、origin/main、ahead/behind、当前 milestone、工作区是否干净、下一步建议

硬规则：
- 全中文 UI
- 不自动 push/release/tag/delete
- 不进入未授权 milestone
- 不绕过 PermissionGate
- 不自动执行危险命令
- 不自动批准权限
- 不提交生成物、缓存、虚拟环境、证书材料、.bolt、uv.lock
- 不使用 as any / unknown as
- renderer 不暴露 ipcRenderer / fs / shell / process
```
