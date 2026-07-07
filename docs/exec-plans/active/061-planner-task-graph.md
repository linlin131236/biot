# M61 执行计划：Planner Task Graph

## 目标
建立 Planner Task Graph 的最小可用模型，把长任务拆成可追踪节点，不直接自动执行。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`：安全边界
- 产品路线图 M61-M70 Agent 工作流核心

## 实现方案

### 后端
- `bolt_core/planner_task_graph.py`：PlannerTaskGraphService
  - 内存存储（dict），不引入大框架
  - TaskGraph：id, title, objective, nodes, timestamps
  - TaskNode：id, title, status, dependencies, risk, owner_role, evidence_refs, timestamps
  - 状态机：pending → in_progress/blocked → completed/failed
  - 依赖检查：节点启动前验证所有依赖已完成
- `bolt_core/planner_task_graph_api.py`：
  - GET /planner/graphs（列表）
  - POST /planner/graphs（创建）
  - GET /planner/graphs/{id}（详情）
  - POST /planner/graphs/{id}/nodes（添加节点）
  - PATCH /planner/graphs/{id}/nodes/{node_id}（状态变更）

### 前端
- PlannerGraphs 组件：展示任务规划图摘要
- 声明"仅规划，不自动执行"

## 安全边界
- 不调用 git/shell/subprocess/harness
- 不绕过 task closure / execution queue / PermissionGate
- 状态变更需通过 API 由用户手动触发

## 验收标准
- [x] 后端数据模型/服务/API
- [x] 状态机：合法转换通过，非法转换阻断
- [x] 依赖检查：未完成的前置依赖阻止节点启动
- [x] 终端状态不可变
- [x] 22 个 targeted tests
- [x] 全量验证通过
- [x] 只是 planner graph，不是 agent 自动执行器
