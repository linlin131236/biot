# M63 决策：Tool Selection Policy

## 决策
新增 ToolSelectionPolicy 作为工具分类和选择验证层，内置 26 种工具注册表。

## 关键设计选择

### 1. 内置注册表而非动态注册
M63 使用 Python dict 作为内置注册表，而非 MCP 式的动态工具发现。原因：
- M63 目标是策略层而不是工具生态（M101+）
- 内置注册表保证了分类的一致性和安全性
- 后续 M101 可扩展为动态注册

### 2. 三级权限模型
- 只读工具：无需权限，直接可用
- 副作用工具：需进入执行队列，人工确认
- 危险工具：需 PermissionGate 明确批准
- 未知工具：拒绝执行

这与 Harness 指南的 s03 权限层（白名单→规则→用户确认）对齐。

### 3. 工具输出不可信原则
ToolSelectionPolicy 的 disclaimer 声明"仅判断分类和权限需求，不执行"。工具的实际执行仍需通过 task closure → execution queue → PermissionGate 管道。

## 不做的
- 不实现 MCP 协议或动态工具注册
- 不执行任何工具
- 不绕过 PermissionGate
- 不自动批准权限
