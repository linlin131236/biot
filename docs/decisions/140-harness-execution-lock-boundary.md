# M140 Decision: Harness Execution Lock Boundary

## 决策

`submit_tool_request()` 在 auto-allowed 分支中只在锁内完成权限判断和 `permission.auto_allowed` 记录，随后释放 `_state_lock`，再执行 `_execute()` 和结果转换。

## 背景

外部复审指出 `Harness.runs` / `Harness.traces` 使用普通 dict 且锁边界较粗。实际验证发现 auto-allowed 工具执行时 `_state_lock` 仍被当前线程持有，会让长耗时只读工具阻塞其他 run 的状态访问。

## 取舍

- 本次只缩小 `submit_tool_request()` 的真实执行锁范围，不重构整个 Harness。
- denied、pending、file.write/file.patch 提案仍保持原有同步路径，避免扩大行为变化。
- `_execute()` 内部仍通过 workspace guard 和各工具自身安全检查兜底。

## 风险控制

- 新增测试断言 `_execute()` 触发时 `_state_lock` 未被当前线程持有。
- 保持 trace 顺序：`permission.evaluated` → `permission.auto_allowed` → `tool.execution.started` → `tool.execution.completed`。
- 不改变 PermissionGate，不新增自动 approve。
