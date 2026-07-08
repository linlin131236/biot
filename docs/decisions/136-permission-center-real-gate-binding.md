# M136 Decision: 权限中心复用既有 PermissionGate 路径

## 决策

权限中心不新增独立批准 API，而是把面板按钮绑定到已有 `/permissions/{request_id}/approve` 和 `/permissions/{request_id}/reject`。

## 原因

已有 PermissionGate 路径包含执行、审计、result ingestion 和 trace 记录。若为权限中心另开批准端点，会产生第二条权限路径，增加绕过和状态不一致风险。

复用现有路径可以保证：

- 批准后行为与主 PermissionGate 完全一致。
- 拒绝后状态与审计链路一致。
- M49 之后的 execution result ingestion 不被绕开。
- 前端只增加一个更方便的人工入口，不增加自动能力。

## 取舍

- 权限中心仍不做批量批准，避免误点高风险操作。
- UI 上显示“批准并执行”，明确该按钮会触发真实执行，不伪装成只读。
- 后端 `id` 与 `request_id` 同时保留，避免破坏旧展示 ID。

## 风险

- 权限中心现在具备真实操作按钮，必须依赖用户点击和按钮文案清楚提示风险。
- 后续若要做二次确认弹窗，需要在前端层继续加，不应改后端 PermissionGate 语义。
