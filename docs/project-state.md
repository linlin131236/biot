# Bolt Project State

## 当前稳定基线
- 已完成到：M125 Public Beta Readiness（M55-M125 最终 Beta Gate，等待爸爸复审）。
- V5 中文产品 UI/UX（M91-M100）已完成并 push。
- V6 工具生态（M101-M110）已完成并 push。
- V7 智能评估 / Agent Dogfood（M111-M120）已完成并 push。
- V8 产品级可靠性（M121-M125）已完成并 push。
- 当前本地分支：`main` 与 `origin/main` 已同步，最新提交以 `git log` 为准。
- 未 release / 未 tag / 未 delete。
- 未进入 M126。

## 当前状态
- 当前阶段：M125 完成并已 push，等待爸爸决定是否进入后续 M126+。
- 本地状态：M121-M125 已完成并 push；HEAD = origin/main。
- 工作区：已跟踪文件干净；`.claude/` 未跟踪、未提交，按规则保持。
- 最新已知远端基线：以 `git log` 为准；当前 `HEAD = origin/main`。
- 最新验证基线：
  - M121-M125 targeted tests：**29 passed**。
  - `uv run pytest -q --color=no`（在 `services/agent-core`）：**1511 passed**，2 warnings。
  - `pnpm --filter @bolt/shared test`：**27 passed**。
  - `pnpm --filter @bolt/desktop test`：**35 files / 268 tests passed**。
  - `pnpm --filter @bolt/desktop build`：通过 (286.08 KB)。
  - `pnpm run quality`：通过。
  - `git diff --check`：通过。
  - `node scripts/check-docs.mjs`：通过。
  - `node scripts/check-chinese-ui.mjs`：通过。
  - 全量测试基线：**1511 backend + 27 shared + 268 desktop = 1806 passed**。

## V8 里程碑结果
- M121：Crash Recovery，只读检查检查点、暂停恢复、会话恢复、审计完整性和接手摘要。
- M122：Data Migration，只读检查 raw/staging/clean/lineage、人工演练和 rollback 计划。
- M123：Update/Rollback，只读检查发布准备、恢复策略、批准边界和禁止自动发布。
- M124：Privacy/Security Audit，只读检查脱敏、权限边界、renderer 暴露、类型逃逸、供应链和隐私审计。
- M125：Public Beta Readiness，聚合最终 Beta 门禁和接手包，完成后停止。

## V8 测试增量
- `test_beta_reliability_common.py`
- `test_crash_recovery.py`
- `test_crash_recovery_api.py`
- `test_data_migration.py`
- `test_data_migration_api.py`
- `test_update_rollback.py`
- `test_update_rollback_api.py`
- `test_privacy_security_audit.py`
- `test_privacy_security_audit_api.py`
- `test_public_beta_readiness.py`
- `test_public_beta_readiness_api.py`
- 当前新增目标测试：**29 tests**。

## 安全扫描目标
- `as any` / `unknown as`：最终验证必须无新增违规。
- renderer 暴露：最终验证必须无新增 `ipcRenderer` / `fs` / `shell` / `process` 暴露。
- 自动执行 / 自动 approve / push-release-tag-delete：最终验证必须无新增违规。
- PermissionGate：不得绕过；M124/M125 只读审计不能替代 PermissionGate。

## 已知风险
- `harnessClientAutonomy.ts` 超过 300 行（历史豁免）。
- M61 Task Graph / M81-M89 多 Agent 工作流以纯内存为主，后续如进入 M126+ 可评估持久化。
- API 测试速度较慢，后续可优化并行执行。
- `.claude/` 未跟踪、未提交，按规则保持。

## 下一步建议
- 完成 full tests / quality / docs / Chinese UI / 安全扫描。
- M121-M125 已 push。
- 后续如进入 M126+，必须由爸爸明确授权；未授权不进入下一阶段。

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
