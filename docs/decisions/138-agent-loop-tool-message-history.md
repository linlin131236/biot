# M138 Decision: 在 run_loop 内维护原生 tool-message 历史

## 决策

M138 在 `AgentLoop.run_loop()` 内维护 messages 列表，把模型 tool_calls 和工具结果以 OpenAI-compatible message 结构传给下一轮。

## 原因

M134 的摘要回填解决了“工具结果完全进不了下一轮”的问题，但它仍不是模型供应商原生的 tool calling 对话结构。真实 coding agent 需要让模型看到结构化工具调用与工具结果，否则多步任务容易退化为“每轮重新猜”。

该方案保留 M134 的 trace 摘要，同时新增：

- assistant tool_calls 消息。
- tool role 结果消息。
- 多 tool_calls 顺序处理。

## 取舍

- `run_step()` 保持单步行为，M138 主要强化 `run_loop()`。
- 多 tool_calls 仍按顺序执行；遇到 pending/denied/failed 立即暂停或停止，不继续执行后续工具。
- 不做并行执行，避免扩大权限和审计复杂度。

## 风险

- messages 历史会增长，后续需要结合 Context Lakehouse/compaction 做截断和检索。
- 真实供应商对 assistant tool_calls 消息格式要求更严格，M138 已在序列化层显式生成 OpenAI-compatible 字段。
