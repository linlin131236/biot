# M129 Exec Plan - Failure And Recovery Lane

## 目标

在 Agent 工作台中展示失败解释和恢复前检查，让爸爸能看到“为什么失败、能否恢复、恢复前必须确认什么”。

## 范围

- 后端 `ProductWorkbenchService` 返回 `failure_recovery`。
- 前端展示“失败与恢复检查”。
- 不自动 retry，不自动 resume，不自动 fix。

## 验收

- 检查项包含失败分类、重试风险、权限复查、状态复查、人工恢复确认。
- 明确 `auto_retry_allowed=false` 和 `auto_resume_allowed=false`。
- targeted backend 和 desktop tests 通过。

