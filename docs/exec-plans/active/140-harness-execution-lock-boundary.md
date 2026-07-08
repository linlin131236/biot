# M140 Harness Execution Lock Boundary Exec Plan

## 目标

缩小 `Harness.submit_tool_request()` 的 `_state_lock` 范围，避免持有全局状态锁时执行真实工具，降低并发 run 下的阻塞和竞态风险。

## 范围

- 新增测试确认 `_execute()` 被调用时当前线程不再持有 `_state_lock`。
- `submit_tool_request()` 仅在记录请求、权限判断、入队 pending、写入提案等共享状态操作时持锁。
- auto-allowed 工具在锁外执行。

## 不做

- 不改变 PermissionGate 决策。
- 不改变 pending permission 语义。
- 不改变 approve/reject API。
- 不新增自动执行权限。

## 验收

- 允许的只读工具执行时不持有 `_state_lock`。
- 原有 harness 权限、拒绝、pending、approve/reject 回归通过。
- full backend、quality、desktop build 全部通过。
