# M138 Agent Loop Tool Message History 执行计划

## 背景

外部复审指出旧 Agent Loop 每步重新构造上下文，并且工具结果只通过摘要进入下一轮；同时只处理第一个 `tool_call`。M134 已经完成安全摘要回填，M138 继续推进到更接近 OpenAI function/tool calling 的 messages 历史结构。

## 目标

1. `run_loop()` 维护同一个 messages 列表。
2. 模型返回 tool_calls 后，追加 assistant tool_calls 消息。
3. 工具执行结果以 `role="tool"` 消息追加到下一轮。
4. 同一轮模型返回多个 tool_calls 时按顺序处理。
5. 默认 loop 上限从 3 调整为 50。
6. 模型网关失败时立即停止，不浪费 50 步。

## 非目标

- 不绕过 PermissionGate。
- 不自动批准 pending permission。
- 不新增并行工具执行。
- 不改变工具安全分类。
- 不移除 M134 的脱敏摘要 trace；它仍作为审计和兼容层保留。

## 实施步骤

1. 增加 tool role messages 红灯测试。
2. 增加多 tool_calls 红灯测试。
3. 增加默认 50 步红灯测试。
4. 扩展 `ModelMessage` 支持 `tool_call_id` 和 `tool_calls`。
5. `OpenAICompatibleGateway` 序列化 tool/assistant tool_calls 消息。
6. `AgentLoop.run_loop()` 维护 messages 历史。
7. 跑 targeted tests、闭环回归、full tests、quality、build 和安全扫描。

## 验收标准

- 第二轮模型请求能看到 `role="tool"` 的工具结果消息。
- 一个模型响应里的多个 tool_calls 都能被执行和回灌。
- 默认 `Harness.run_agent_loop()` 为 50 步。
- LLM 失败只调用一次并立即返回 failed。
- pending permission 仍暂停，不继续执行后续工具。
