# M65 决策：Safe Retry Loop

## 决策
新增 SafeRetryLoop，集成 M63 ToolSelectionPolicy 和 M64 FailureClassifier 做受控重试判断。

## 关键设计选择

### 1. 双重安全门
重试判断同时检查失败类别和工具危险度：
- 失败类别门：security_block / permission_waiting 禁止重试
- 工具危险度门：dangerous 类工具禁止重试
- 次数门：超过 max_attempts 停止

### 2. 审计历史
每次 retry 调用 record_retry() 都会记录：attempt 序号、失败类别、错误文本摘要、是否允许、时间戳。这为后续审计提供了可追溯的重试记录。

### 3. 与 PermissionGate 的关系
SafeRetryLoop 不绕过 PermissionGate。即使 retry 被允许，实际操作仍需要通过 task closure → execution queue → PermissionGate 管道。

## 不做的
- 不实际执行重试（只判断和记录）
- 不绕过 PermissionGate
- 不自动批准权限
- 不无限重试
