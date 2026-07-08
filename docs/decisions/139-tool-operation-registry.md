# M139 Decision: Tool Operation Registry

## 决策

新增 `tool_operations.py` 作为工具名到操作类型的唯一代码入口，AgentLoop 和 FakeModelGateway 统一调用 `operation_for_tool()`。

## 背景

外部复审指出工具定义和操作映射存在重复。实际验证发现 `model_gateway.py` 的测试桩映射缺少 `file.patch`、terminal、web 等工具，导致 `file.patch` 在 fake gateway 内容中被误标为 `read`。

## 取舍

- 选择轻量共享模块，而不是重写完整 tool registry。
- 保持未知工具默认 `read`，避免测试桩生成更高权限操作。
- 不改变 PermissionGate 的权限判断，权限边界仍由 `permission_gate.py` 执行。

## 风险控制

- 新增测试覆盖 `file.patch`、terminal、web 映射。
- `agent_loop.py` 和 `model_gateway.py` 不再保留私有映射。
- 本改动只影响模型请求与测试桩的操作类型一致性，不新增执行入口。
