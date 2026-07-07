# Decision 084 — Subtask Assignment

## 决策
子任务分派模型：Planner 拆解为结构化子任务，支持角色兼容性检查、依赖管理、风险分级。

## 关键设计
- 7 种状态：pending → ready → in_progress → awaiting_review → completed / blocked / failed
- 4 级风险：low/medium/high/critical，high+ 需人工确认
- 角色兼容矩阵：planner→plan, researcher→research, builder→build, reviewer→review
- Researcher 不能 write/execute，Reviewer 不能 assigned_to Builder

## 结果
- 16 tests 通过
