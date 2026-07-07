# Beta Update Rollback Plan

## 原则
- manual update 必须由爸爸人工触发。
- manual rollback 必须有明确人工步骤和验证命令。
- release readiness 必须先通过。
- approval 必须来自人工确认，不允许 agent self-approval。
- no auto publish：不自动发布、不自动 tag、不自动 delete。

## 当前结论
M123 只检查升级回滚准备度，不会发布、回滚、tag 或删除。
