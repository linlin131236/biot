# M139 Tool Operation Registry Exec Plan

## 目标

把工具名到操作类型的映射收拢为单一注册表，避免 AgentLoop、模型网关、测试桩各自维护不同映射，导致 `file.patch` 等写入工具被误标为只读操作。

## 范围

- 新增共享工具操作映射模块。
- AgentLoop 提交 tool call 时使用共享映射。
- FakeModelGateway 生成测试内容时使用共享映射。
- 新增测试覆盖 patch、terminal、web 等工具操作映射。

## 不做

- 不改变 PermissionGate 决策。
- 不新增工具执行能力。
- 不自动 approve。
- 不修改桌面 UI。

## 验收

- `file.patch` 必须映射为 `patch`。
- terminal 工具必须映射为 `spawn` / `poll` / `kill`。
- web extract 必须映射为 `extract`。
- 未知工具默认保持只读形态 `read`。
- targeted tests、full backend、quality、build 全部通过。
