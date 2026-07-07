# M59 决策：Rollback and Recovery Policy

## 决策
新增 RecoveryPolicyService，以静态策略文档形式提供 10 个故障场景的人工恢复步骤。

## 关键设计选择

### 1. 静态策略而非动态诊断
RecoveryPolicyService 返回预定义的策略内容，不尝试动态检测当前系统状态。原因：
- 避免在恢复策略中引入新的执行路径
- 策略内容是稳定的最佳实践，适合作为参考文档
- 动态诊断可能会触发只读 git 操作，增加复杂性

### 2. 分类覆盖
5 个分类覆盖 Bolt 当前架构的主要故障面：
- 审计完整性（文件损坏/缺失）
- 发布失败（push 被拒/tag 冲突）
- 权限误操作（误批准/绕过）
- 任务中断（loop 中断/进程崩溃）
- 数据损坏（文档不一致/gate 缺失）

### 3. 严重度分级
- critical：安全红线，必须立即处理（perm_gate_bypass）
- high：核心功能受损（audit_corrupt, release_push_rejected, process_crash, perm_misapproval）
- medium：功能降级（audit_missing, task_interrupted, etc.）
- low：非紧急（docs_inconsistent）

### 4. 恢复步骤格式
每个步骤以"1. 2. 3."编号，包含具体可执行的终端命令或 UI 操作。不引用内部 API 路径，面向爸爸级别的操作者。

## 不做的
- 不自动执行 git reset/revert/delete
- 不提供"一键恢复"按钮
- 不绕过 PermissionGate
- 不创建自动恢复脚本
