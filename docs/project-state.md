# Bolt Project State

## 当前稳定基线
- 已完成到：M120 Agent Intelligence Dogfood（V7 终点，等待爸爸复审）。
- V5 中文产品 UI/UX（M91-M100）已完成并 push。
- V6 工具生态（M101-M110）已完成并 push。
- V7 智能评估 / Agent Dogfood（M111-M120）已完成并 push。
- 远程状态：`origin/main` 与本地 `HEAD` 已同步，最新提交以 `git log` 为准。
- 当前本地分支：`main` 与 `origin/main` 已同步。
- 未 release / 未 tag / 未 delete。
- 未进入 M121。

## 当前状态
- 当前阶段：M120 完成并已 push，等待爸爸授权后再进入 M121。
- 工作区：已跟踪文件干净；`.claude/` 未跟踪、未提交，按规则保持。
- 最新验证基线：
  - `uv run pytest -q --color=no`（在 `services/agent-core`）：**1482 passed**，2 warnings。
  - `pnpm --filter @bolt/shared test`：**27 passed**。
  - `pnpm --filter @bolt/desktop test`：**35 files / 268 tests passed**。
  - `pnpm --filter @bolt/desktop build`：通过 (286 KB)。
  - `pnpm run quality`：通过。
  - `git diff --check`：通过。
  - `node scripts/check-docs.mjs`：通过。
  - `node scripts/check-chinese-ui.mjs`：通过。
  - 全量测试基线：**1482 backend + 27 shared + 268 desktop = 1777 passed**。

## V7 里程碑结果
- M111：工具调用评估基准（Tool Call Eval）。
- M112：补丁应用评估（Patch Apply Eval）。
- M113：测试失败诊断评估（Test Failure Diagnosis Eval）。
- M114：权限边界评估（Permission Boundary Eval）。
- M115：多 Agent 协作评估（Multi-Agent Collaboration Eval）。
- M116：记忆检索质量评估（Memory Retrieval Eval）。
- M117：中文交互质量评估（Chinese Interaction Eval）。
- M118：端到端任务复盘（E2E Task Dogfood）。
- M119：失败恢复复盘（Failure Recovery Dogfood）。
- M120：智能 Agent 大复盘（Agent Intelligence Dogfood）。

## V7 测试增量
- M111: +18 tests（tool_call_eval）
- M112: +16 tests（patch_apply_eval）
- M113: +12 tests（test_failure_diagnosis_eval）
- M114: +12 tests（permission_boundary_eval）
- M115: +10 tests（multi_agent_collaboration_eval）
- M116: +10 tests（memory_retrieval_eval）
- M117: +12 tests（chinese_interaction_eval）
- M118: +11 tests（e2e_task_dogfood）
- M119: +7 tests（failure_recovery_dogfood）
- M120: +5 tests（agent_intelligence_dogfood）
- V7 当前合计：+113 tests（10 个后端 eval/dogfood 模块）

## 安全扫描结果
- `as any` / `unknown as`：0 新增违规。
- renderer 暴露：无新增 `ipcRenderer` / `fs` / `shell` / `process` 暴露。
- 自动执行 / 自动 approve / push-release-tag-delete：无新增违规。
- PermissionGate：不得绕过；M120 复查 approval apply 与 permission contract。

## 已知风险
- `harnessClientAutonomy.ts` 超过 300 行（已记录豁免）。
- M61 Task Graph / M81-M89 多 Agent 工作流以纯内存为主，后续最终收口阶段评估持久化。
- API 测试速度较慢，后续可优化并行执行。
- `.claude/` 未跟踪、未提交，按规则保持。

## 下一步建议
- 爸爸复审 M111-M120 后，可授权 push。
- 最后一批为 M121-M125：Beta 收口、技术债清理、安全门禁最终复查、最终发布准备。

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
