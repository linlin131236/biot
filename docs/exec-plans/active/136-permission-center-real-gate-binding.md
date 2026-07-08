# M136 Permission Center Real Gate Binding 执行计划

## 背景

M92 权限中心只做只读展示，真实批准/拒绝仍在主 PermissionGate 面板中。外部审核指出产品闭环需要更直接：爸爸在权限中心看到待批准项后，应能通过同一条 PermissionGate 路径手动批准或拒绝，而不是只看说明。

## 目标

1. 权限中心展示项包含真实 `request_id`。
2. 桌面端权限中心复用既有 `/permissions/{request_id}/approve` 与 `/reject`。
3. 批准/拒绝必须由用户点击触发，不自动执行。
4. 操作完成后刷新权限中心列表并显示中文结果。
5. 保留 PermissionGate 审计和 result ingestion 语义。

## 非目标

- 不新增后端批准端点。
- 不自动 approve。
- 不绕过 PermissionGate。
- 不新增批量批准。
- 不改变权限风险分类规则。

## 实施步骤

1. 增加后端 API 测试，验证 permission-center item 的 `request_id` 可用于真实 approve。
2. 增加前端测试，验证按钮点击后才调用 approve/reject。
3. 为 `PermissionCenterItem` 增加 `request_id`。
4. 为 desktop client 增加权限中心 approve/reject 包装函数。
5. 更新 `PermissionCenterPanel`，增加中文按钮、处理中状态、结果提示和刷新。
6. 跑 targeted tests、full tests、quality、build 和安全扫描。

## 验收标准

- 权限中心 item 的 `id` 仍是展示 ID，`request_id` 用于真实 PermissionGate API。
- 点击“批准并执行”后调用 `/permissions/{request_id}/approve`。
- 点击“拒绝”后调用 `/permissions/{request_id}/reject`。
- 没有自动批准、自动执行或绕过权限门。
- 所有用户可见文字为中文。
