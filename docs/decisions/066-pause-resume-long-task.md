# M66 决策：Pause/Resume Long Task

## 决策
新增 PauseResumeService，以快照机制实现节点暂停/恢复，集成 M62 StateMachine 的状态转换规则。

## 关键设计选择

### 1. 快照式暂停
暂停时捕获完整快照：暂停前状态、时间戳、原因、证据引用。恢复时基于快照验证完整性，而非凭空恢复。

### 2. 只能从活跃状态暂停
仅允许从 running 或 ready 状态暂停。pending/blocked 不应被暂停（还没开始），completed/failed 不能暂停（已结束）。

### 3. 恢复三重检查
- 快照完整性：确保快照存在且未损坏
- 权限重新验证：标记 requires_human_decision，要求通过 PermissionGate
- 状态转换验证：paused → ready 是否合法（由 M62 StateMachine 验证）

### 4. 取消暂停 = 失败
cancel_pause 将节点标记为 failed（终端状态），而非删除快照。保留审计记录。

## 不做的
- 不自动执行恢复后的操作
- 不绕过 PermissionGate
- 不自动批准权限
- 不在暂停期间执行任何副作用步骤
