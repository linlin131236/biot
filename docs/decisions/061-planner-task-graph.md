# M61 决策：Planner Task Graph

## 决策
新增 PlannerTaskGraphService，以内存存储实现最小可用的任务规划图模型。

## 关键设计选择

### 1. 内存存储
选择 dict 内存存储而非文件持久化：
- M61 是 V2 Agent 工作流的起点，先验证模型正确性
- 后续 M62+ 可以在状态机稳定后添加持久化
- 避免引入文件系统依赖和并发问题

### 2. 状态机设计
```
pending → in_progress → completed
  ↓          ↓             (终端)
blocked  → in_progress → failed
  ↓                       ↓
  └── pending ←───────────┘
```
- completed 是终端状态，不可再变
- failed 只能回到 pending
- blocked 可回到 pending 或 in_progress

### 3. 依赖检查
节点从 pending → in_progress 时，强制检查所有 dependencies 是否都是 completed。这确保任务规划图有正确的执行顺序。

### 4. 与执行系统的分离
PlannerTaskGraph 是纯规划层：
- 节点不代表自动执行
- 节点状态变更由用户手动触发
- evidence_refs 字段用于关联实际的 closure/handoff 记录
- 不调用 git、shell、harness、PermissionGate

## 不做的
- 不实现自动调度
- 不引入 LangGraph 或类似框架
- 不持久化（留给 M62+）
- 不连接 Agent Loop
- 不绕过 PermissionGate
