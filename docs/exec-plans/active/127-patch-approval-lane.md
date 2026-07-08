# M127 Exec Plan - Patch Approval Lane

## 目标

在 Agent 工作台中补齐补丁批准检查清单，让爸爸能清楚看到 apply 前必须满足哪些条件。

## 范围

- 后端 `ProductWorkbenchService` 返回 `patch_approval`。
- 前端 `ProductWorkbenchPanel` 展示补丁批准检查。
- 不新增批准按钮，不自动 apply。

## 验收

- 检查项包含补丁预览、目标范围锁定、人工批准、过期复查、审计记录。
- UI 显示中文“补丁批准检查”。
- targeted backend 和 desktop tests 通过。

