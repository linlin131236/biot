# M68 Agent Budget Controls — 设计决策

## 决策背景
Agent Loop 已有 `max_steps` 参数，Goal 已有 `max_steps`/`max_cost`/`max_wall_time` 字段，ContextBuilder 有 `DEFAULT_TOKEN_BUDGET`。但这些分散在各处，没有统一的预算检查点。M68 把它们整合为一个 gatekeeper service。

## 决策 1：外层 gatekeeper，不侵入 agent_loop
**选择**：`AgentBudgetService` 作为独立检查器，挂在 agent_loop 调用前/步骤间。

**理由**：
- Harness s04 Hooks 原则：扩展挂在循环上，不写进循环里
- agent_loop 保持简单，预算逻辑独立可测试
- 可在任何步骤间插入预算检查

## 决策 2：四维预算统一模型
**选择**：`BudgetConfig(max_steps, max_tool_calls, max_runtime_seconds, max_context_tokens)` + `BudgetState(steps_used, tool_calls_used, start_time, context_tokens_used)`。

**理由**：
- steps：已有基础（agent_loop max_steps），需要独立计数器
- tool_calls：M63 Tool Selection Policy 工具调用需要上限
- runtime：长时间任务需要超时保护
- context_tokens：ContextBuilder 已有 token_budget 概念

## 决策 3：安全默认值
**选择**：缺失预算时使用保守默认值：
- `max_steps` 未指定 → 50
- `max_tool_calls` 未指定 → 100
- `max_runtime_seconds` 未指定 → 1800（30 分钟）
- `max_context_tokens` 未指定 → 8000

**理由**：安全优先，宁可过早阻断也不无限执行。

## 决策 4：阻断只返回原因，不自动继续
**选择**：`check()` 返回 `allowed=False` + 中文阻断原因 + 建议动作，由调用方决定下一步。

**理由**：
- 对齐文档要求："不自动提高预算，不自动继续执行"
- 阻断是信号，不是自动 kill
- 调用方（harness/goal runner）可以决定暂停、通知用户、或人工超控

## 风险
- 时间检查依赖调用方传入 `elapsed_seconds`（不主动计时，避免引入后台线程）
- 上下文 token 计数需调用方传入（tokens_used），无自动 tokenizer 依赖
