# M52 Permission Request Recovery

## 验收标准
- 同一进程内重复 request-permission 不产生重复 pending permission。
- 模拟重启后 audit store 恢复 `waiting_permission` handoff，但新的 `PermissionQueue` 为空时，再次 request-permission 会安全生成新的 pending permission。
- 新 pending 继续绑定 closure 对应 run 的 workspace，不回退到静态 workspace。
- completed/failed handoff 禁止重新申请权限。
- request-permission 不调用 approve_permission、submit_tool_request、shell executor 或 Agent Loop。

## 最小边界
- 只给 `PermissionQueue` 增加只读查询能力。
- 只修改 `ExecutionPermissionBridgeService.request_permission` 的已有 request 路径。
- 不持久化 approved 状态，不自动恢复执行。
- 不新增 UI 入口，不新增执行能力。

## 验证
- 新增 `tests/test_permission_request_recovery.py` 覆盖进程内幂等、重启恢复、run/workspace 绑定、终态拒绝、无执行调用。
- 保留既有 permission bridge 和 workspace API 测试。
