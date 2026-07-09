# M154 Audit Timeline Live 执行计划

## 目标

把审计时间线接入真实执行审计数据，并在进入桌面 UI 前对 title/reason/result 等摘要字段脱敏。

## 验收标准

- `/audit-timeline` 支持按事件来源筛选。
- 审计时间线不展示 token、API key、私钥等敏感内容。
- 桌面面板显示中文筛选项。
- targeted tests、desktop tests、quality、Chinese UI、diff check 通过。

## 风险

- 脱敏必须在后端输出前完成，不能只依赖前端遮罩。
- source filter 必须保持只读，不改变审计记录。
