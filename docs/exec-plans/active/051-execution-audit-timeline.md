# M51 Execution Audit Timeline

## 验收标准
- 给定 `closure_id`，后端返回按时间排序的只读执行审计时间线。
- 时间线覆盖 queue proposed/approved、handoff created、permission requested、permission approved/rejected、result ingested、closure evidence recorded。
- API 只返回审计摘要，不新增执行、批准、拒绝或 PermissionGate 绕过能力。
- 空闭环返回空数组；不存在的 closure 按既有风格返回 404。
- 桌面 UI 只读展示中文状态：待处理、已批准队列、已申请权限、等待权限、已执行、已拒绝、已失败。

## 最小边界
- 只读取 `ExecutionQueueService`、`ExecutionHandoffService`、`TaskClosureService` 的既有状态。
- 不持久化新的执行状态，不新增执行器调用。
- 不新增 approve/reject/request-permission 入口。
- 前端只新增 fetch 与展示，不触碰 renderer 能力边界。

## 验证
- 后端单元测试覆盖正常链路、空链路、跨 closure 隔离。
- API 测试覆盖 200/404 和中文字段稳定。
- 桌面 vitest 覆盖 fetch 与只读展示。
