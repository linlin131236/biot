# Bolt Project State

## 当前稳定基线
- 已完成到：M125 Public Beta Readiness（M55-M125 最终 Beta Gate，等待爸爸复审）。
- V5 中文产品 UI/UX（M91-M100）已完成并 push。
- V6 工具生态（M101-M110）已完成并 push。
- V7 智能评估 / Agent Dogfood（M111-M120）已完成并 push。
- V8 产品级可靠性（M121-M125）本地已完成，待爸爸复审后决定是否 push。
- 当前本地分支：`main` 领先 `origin/main`，最新提交以 `git log` 为准。
- 未 release / 未 tag / 未 delete。
- 未进入 M126。

## 当前状态
- 当前阶段：M125 完成，等待爸爸复审；不自动 push。
- 本地状态：M121-M125 已完成，未 push。
- 工作区：M121-M125 收口改动待提交；`.claude/` 未跟踪、未提交，按规则保持。
- 最新已知远端基线：`f2e25c5 docs: mark M111-M120 pushed`。
- 当前验证进度：
  - M121-M125 targeted tests：**22 passed**。
  - full backend / shared / desktop / build / quality：待最终提交前运行。

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
- 当前新增目标测试：**22 tests**。

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
- 提交 M121-M125 每个 milestone 的 commit。
- 爸爸复审通过后，再由爸爸明确授权是否 push。

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
