# M165 Decision: Gate Freeze

## 决策

采用共享 `GateFreezeService` 状态作为 Gate Freeze 单一来源，并让自动继续、自主循环和批准应用入口读取该状态。

## 原因

孤岛式冻结面板无法保护真实执行链。共享状态能确保后续入口在同一冻结边界下工作。

## 后果

- Gate 冻结返回 423，调用方必须停止。
- 解冻需要显式调用 `/gate/unfreeze`。
- 后续若引入持久化 Gate 状态，应保持同一服务边界。
