# M62 决策：Execution State Machine

## 决策
新增 ExecutionStateMachine，作为独立的状态转换验证层，与 M61 TaskNode 的状态管理分离。

## 关键设计选择

### 1. 独立验证层
ExecutionStateMachine 是纯函数式验证层，不持有状态。状态由调用方（TaskGraph、ExecutionQueue 等）维护。原因是：
- 避免与 M61 的 in-memory 存储耦合
- 允许多个系统复用同一套转换规则
- 简化测试（无状态依赖）

### 2. 8 种状态设计
```
pending → ready → running → completed
  ↓        ↓         ↓
blocked  blocked  waiting_permission → running
                   ↓                   ↓
                  failed             paused → ready
                   ↓                  ↓
                  (终端)            failed
```
- pending：初始态，依赖/条件未满足
- ready：前置满足，可以执行
- running：执行中
- waiting_permission：等待 PermissionGate 批准
- paused：人工暂停
- completed：成功（终端）
- failed：失败（终端）
- blocked：被依赖/条件阻塞

### 3. 与 PermissionGate 的协作
waiting_permission 状态是专门为与现有 PermissionGate 对接设计的。当节点进入 running 后遇到需要权限的操作，可以转换到 waiting_permission，等待批准后回到 running。

### 4. 终端状态不可逆
completed 和 failed 是终端状态，不能转换到任何其他状态。这防止了完成的节点被意外重新执行。

## 不做的
- 不持有节点状态（纯验证）
- 不自动执行节点
- 不跳过 waiting_permission → PermissionGate 流程
- 不修改 task closure / execution queue
