# M166 Decision: Tool Verification

## 决策

工具验证仅做只读健康检查，不执行工具本体。

## 原因

Loop 需要证据化检查，但验证本身不能扩大权限或触发副作用。

## 后果

工具状态可被 UI 和 review gate 引用，但不能替代 PermissionGate。
