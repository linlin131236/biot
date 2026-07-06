# Decision 052: Permission Request Recovery

## 决策
当 handoff 已记录 `permission_request_id` 但当前进程的 `PermissionQueue` 没有对应 pending item 时，允许在 handoff 仍处于 `waiting_permission` 的前提下重新创建 pending permission，并替换为新的 `permission_request_id`。

## 原因
pending permission 是进程内状态。应用重启后 audit store 会恢复 handoff 的 `waiting_permission`，但 PermissionQueue 为空，UI 看不到可批准项；旧逻辑又因为已有 `permission_request_id` 直接返回，导致用户无法继续人工批准。

## 约束
- 不持久化已批准状态。
- 不自动执行，不自动 approve，不绕过 PermissionGate。
- completed/failed handoff 不允许重新申请。
- 新 pending 仍使用 M50 P1 的 closure/run workspace resolver。

## 方案
- `PermissionQueue` 增加 `get` / `has_pending` 只读查询。
- bridge 遇到已有 request id：
  - queue 中仍有 pending：幂等返回。
  - queue 中没有 pending 且 handoff 等待权限：重新创建 ToolRequest，更新 handoff permission_request_id，并记录 bridge_error 说明旧请求已过期。
  - handoff 已 completed/failed：拒绝重新申请。
