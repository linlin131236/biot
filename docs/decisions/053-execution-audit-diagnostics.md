# Decision 053: Execution Audit Consistency Diagnostics

## 决策
新增只读 execution audit diagnostics 聚合层，检查 queue、handoff、pending permission、closure evidence 的一致性，并通过后端 API 和桌面 UI 展示中文诊断结果。

## 原因
M51 提供时间线，M52 修复 pending permission 重启恢复风险。下一步需要发现仍然可能存在的不一致状态，但不能自动修复或绕过人工权限边界。

## 约束
- 不做 auto-fix。
- 不自动执行，不自动 approve，不绕过 PermissionGate。
- 不新增 shell/fs/process/ipcRenderer renderer 能力。
- UI 文案中文。

## 方案
- 新增 `execution_audit_diagnostics.py`。
- 新增 GET `/execution-audit/diagnostics`，可选 `closure_id`。
- shared 增加 `ExecutionAuditDiagnostic` 类型。
- desktop client 增加 `fetchExecutionAuditDiagnostics`。
- `ExecutionHandoffPanel` 附近增加只读诊断展示。
