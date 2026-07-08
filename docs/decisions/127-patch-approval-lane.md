# M127 Decision - Patch Approval Lane

## 决策

把补丁批准做成只读检查清单，而不是可点击批准控件。

## 理由

- 批准权必须留在 PermissionGate / approval apply 既有边界里。
- 工作台的责任是让爸爸看懂风险和下一步，不替代人工授权。
- 检查清单比单个警告更适合长期扩展。

## 安全边界

- 不调用 approve API。
- 不调用 apply API。
- 不隐藏过期复查和审计要求。

