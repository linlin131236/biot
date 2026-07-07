# M62 执行计划：Execution State Machine

## 目标
在 M61 Task Graph 基础上建立执行状态机，只管理状态，不自动绕过权限执行。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_AgentHarness20层进化指南.md`：Agent Loop、状态机、停止条件
- M61 Planner Task Graph：状态机对接基础

## 实现方案

### 后端
- `bolt_core/execution_state_machine.py`：ExecutionStateMachine
  - 8 种状态：pending, ready, running, waiting_permission, paused, completed, failed, blocked
  - 合法转换表：18 条转换，completed/failed 为终端状态
  - validate_transition / can_transition / allowed_transitions
  - 全中文状态标签
- `bolt_core/execution_state_machine_api.py`：
  - GET /execution/state-machine/summary（全量定义）
  - GET /execution/state-machine/transitions/{from_state}（允许的下一步）
  - POST /execution/state-machine/validate（验证转换）

### 与现有系统共存
- 不修改 task closure / execution queue / PermissionGate
- 纯验证层，不执行任何操作
- 可与 M61 TaskNode 状态对接

## 验收标准
- [x] 8 种状态 + 全中文标签
- [x] 合法/非法转换覆盖
- [x] 终端状态不可变
- [x] 25 个 targeted tests
- [x] 不新增自动执行入口
