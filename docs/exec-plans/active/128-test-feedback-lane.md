# M128 Exec Plan - Test Feedback Lane

## 目标

在 Agent 工作台中展示白名单测试回填，让爸爸知道哪些测试可用于验证，以及系统不会接受任意 shell。

## 范围

- 后端 `ProductWorkbenchService` 返回 `test_feedback`。
- 前端展示“白名单测试回填”。
- 不新增命令输入框，不自动运行测试。

## 验收

- 测试清单包含后端单元、后端 API、共享模块、桌面测试、桌面构建、全量质量门。
- 明确 `arbitrary_shell_allowed=false`。
- targeted backend 和 desktop tests 通过。

