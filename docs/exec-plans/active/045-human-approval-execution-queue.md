# M45 Human Approval Execution Queue

## 目标
把 M44 的下一步建议、修复建议、命令建议转成安全执行队列。队列项由用户查看、批准、拒绝、标记完成或失败。

## 范围
- 新增 ExecutionQueueItem 与 ExecutionQueueService。
- 从 TaskClosure assessment / verification plan 生成待处理动作。
- 新增 execution queue API。
- shared protocol 与 desktop client 支持 queue 类型和端点。
- 新增 ExecutionQueuePanel 中文 UI。
- TaskClosure 区域接入安全执行队列。

## 不做
- 不自动执行 shell。
- 不自动批准 PermissionGate 请求。
- 不自动 push / release / delete。
- 不把 verification command 直接变成执行。
- 不绕过 PermissionGate。
- 不进入 M46。

## 队列语义
队列项只是待处理动作记录。`approve` 只代表用户批准该队列项继续被人工处理，不等于 `/permissions/{id}/approve`，也不会触发 Harness、shell 或 Agent Loop。

## 风险等级
- `read_only`：只读或人工审查动作。
- `verification_command`：建议用户运行验证命令，但系统不执行。
- `workspace_write`：可能涉及工作区写入，必须人工处理。
- `destructive`：高风险动作，只允许记录，不自动完成。

## 状态
- `pending`：待批准。
- `approved`：队列项已批准，但仍未自动执行。
- `rejected`：用户拒绝并记录原因。
- `completed`：用户标记外部或人工动作已完成。
- `failed`：用户标记动作失败。

## 验证
- Execution Queue service / API：22 passed。
- Execution Queue integration smoke：1 passed。
- shared protocol：24 passed。
- desktop client / panel / dogfood 最小验证：通过。
