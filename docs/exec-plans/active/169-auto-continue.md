# M169 Auto Continue 执行计划

## 目标

新增自动继续状态控制，允许 Loop 在安全 Gate 通过后继续下一轮。

## 验收标准

- `/orchestrator/auto-continue` 可开启/关闭自动继续。
- `/orchestrator/auto-continue/status` 可只读查询状态。
- Gate 冻结时拒绝变更自动继续状态。
- 桌面面板中文展示状态。
- targeted tests、quality、Chinese UI、diff check 通过。

## 风险

- 自动继续不是自动批准；任何写入仍需原有批准链路。
- Gate Freeze 必须优先生效。
