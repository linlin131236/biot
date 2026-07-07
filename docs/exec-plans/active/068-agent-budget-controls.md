# M68 Agent Budget Controls — 执行计划

## 目标
给 Agent 长任务加预算控制，限制步数、时间、工具调用、上下文 token。先判断和阻断，不做自动扩容。

## 参考资料
| # | 文件 | 采用原则 |
|---|------|---------|
| 1 | `AI工程-Phase14-Agent工程-深度笔记-上.md` | Lesson 01：轮次预算——"根据任务类别设定上限，不要一刀切"；停止条件是 Agent Loop 五大必需品之一 |
| 2 | `20260628_AgentHarness20层进化指南.md` | s01 循环：while True + stop_reason 判断；预算检查是停止条件的一种 |
| 3 | `桌面AI编程Agent全流程架构对比.md` | 关键数据流中 Permisson Check → Execute 之间应插入 Budget Check |

## 范围
- 新增 `AgentBudgetService`：四维预算（steps, tool_calls, runtime, context_tokens）
- 新增 API router：budget check 端点
- 不修改 agent_loop（挂在外层，不侵入循环）
- 不自动扩容、不自动继续

## 产出文件
- `services/agent-core/src/bolt_core/agent_budget.py`
- `services/agent-core/src/bolt_core/agent_budget_api.py`
- `services/agent-core/tests/test_agent_budget.py`
- `services/agent-core/tests/test_agent_budget_api.py`
- 修改 `app.py` 注册 router
- `docs/exec-plans/active/068-agent-budget-controls.md`
- `docs/decisions/068-agent-budget-controls.md`
- `docs/phase-68-review-gate.md`

## 验收标准
- [ ] 预算内 allowed
- [ ] 超步数 blocked + 中文原因
- [ ] 超工具调用 blocked + 中文原因
- [ ] 超时间 blocked + 中文原因
- [ ] 超上下文 blocked + 中文原因
- [ ] 缺失预算走安全默认
- [ ] 不自动提高预算
- [ ] API tests + service tests 完整
