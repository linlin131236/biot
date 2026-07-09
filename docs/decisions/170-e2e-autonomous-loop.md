# M170 Decision: E2E Autonomous Loop

## 决策

M170 提供受限诊断闭环，返回角色 trace 与 verdict，不执行危险动作。

## 原因

在真实产品可用前，需要先证明 Loop 的状态、轮次和 Gate 边界可观测、可停止、可审计。

## 后果

后续要接入真实 Builder 写入时，必须继续通过 PermissionGate、approval apply 和 Gate Freeze。
