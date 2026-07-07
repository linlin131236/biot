# Bolt Project State

## 当前稳定基线
- 已完成到：M110 工具生态大复盘（V6 终点，等待爸爸复审）
- V5 中文产品 UI/UX（M91-M100）已完成并 push。
- V6 工具生态（M101-M110）已完成，未 push。
- 远程状态：`origin/main` 在 `abaee62`（M100 推送点）。
- 当前本地分支：`main`，领先 `origin/main` 9 commits（M101-M110）。
- 未 release / 未 tag / 未 delete。
- 未进入 M111。

## 当前状态
- 当前阶段：M110 完成，等待爸爸复审后决定是否 push 和/或进入 M111。
- 工作区：已跟踪文件干净；`.claude/` 未跟踪、未提交，按规则保持。
- 最新验证基线：
  - `uv run pytest -q --color=no`（在 `services/agent-core`）：**1385 passed**（1130 unit + 255 API）。
  - `pnpm --filter @bolt/shared test`：**27 passed**。
  - `pnpm --filter @bolt/desktop test`：**35 files / 268 tests passed**。
  - `pnpm --filter @bolt/desktop build`：通过 (286 KB)。
  - `pnpm run quality`：通过。
  - `git diff --check`：通过。
  - `node scripts/check-docs.mjs`：通过。
  - `node scripts/check-chinese-ui.mjs`：通过。
- 全量测试基线：**1385 backend + 27 shared + 268 desktop = 1680 passed**。

## V6 里程碑结果
- M101：工具注册表（Tool Registry）。
- M102：工具能力声明（Tool Manifest）。
- M103：工具权限契约（Tool Permission Contract）。
- M104：只读工具运行器（Read-only Tool Runner）。
- M105：写入工具提案（Write Tool Proposal）。
- M106：补丁提案结构（Patch Proposal）。
- M107：中文补丁预览 UI（Patch Preview UI）。
- M108：批准后应用补丁（Approval Apply）。
- M109：测试运行接入（Test Runner Integration）。
- M110：工具生态大复盘（Tool Ecosystem Dogfood）。

## V6 测试增量
- M101: +25 tests（tool_registry）
- M102: +22 tests（tool_manifest）
- M103: +24 tests（tool_permission_contract）
- M104: +26 tests（readonly_tool_runner）
- M105: +21 tests（write_tool_proposal）
- M106: +20 tests（patch_proposal）
- M107: +6 tests（PatchPreviewPanel.tsx）
- M108: +10 tests（approval_apply）
- M109: +7 tests（test_runner_integration）
- M110: +5 tests（tool_ecosystem_dogfood）
- **V6 合计：+166 tests，+9 后端服务，+1 桌面面板**

## 安全扫描结果
- `as any` / `unknown as`：0 新增
- renderer 暴露：无 ipcRenderer/fs/shell/process
- 自动执行/批准：无 bypass
- 架构边界：已为 V6 工具文件豁免 subprocess（仅限只读 git 和白名单测试命令）

## 已知风险
- `harnessClientAutonomy.ts` 超过 300 行（已记录豁免）
- M61 Task Graph / M81-M89 多 Agent 工作流以纯内存为主
- API 测试速度较慢（~6 min），后续可优化
- `.claude/` 未跟踪、未提交，按规则保持

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
- 代码文件尽量保持在 300 行以内。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
