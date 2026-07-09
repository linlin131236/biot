# M165 Gate Freeze 执行计划

## 目标

新增生产级 Gate Freeze：当 Gate 冻结时，批准应用、自动继续和自主循环启动必须被阻断。

## 验收标准

- Gate 冻结状态由共享服务维护，而不是孤岛 UI 状态。
- `/gate/freeze`、`/gate/unfreeze`、`/gate/status` 可用。
- Gate 冻结时 `/orchestrator/auto-continue` 与 `/orchestrator/autonomous-loop` 返回 423。
- Gate 状态面板为中文 UI，无危险操作入口。
- targeted tests、quality、Chinese UI、diff check 通过。

## 风险

- 如果 Gate 只显示状态但不阻断动作，则视为失败。
- 不能绕过 PermissionGate 或自动批准权限。
