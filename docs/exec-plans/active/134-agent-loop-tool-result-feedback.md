# M134 Agent Loop Tool Result Feedback 执行计划

## 背景

M133 解决了默认 fake 模型问题。下一步需要让 Agent Loop 更接近真实 coding agent：模型发起 tool call 后，工具结果必须进入下一轮 LLM 上下文，而不是只通过 trace event type 粗略提示。

## 目标

1. 工具执行结果写入结构化 trace。
2. 下一轮 Planner prompt 包含最近工具结果摘要。
3. 工具输出进入 LLM 前必须脱敏并限制长度。
4. 模型在拿到工具结果后可直接文本总结完成 loop。

## 非目标

- 不改 OpenAI function-calling 的消息格式为原生 tool role；本 milestone 先用现有 Planner 架构做安全回填。
- 不改变 PermissionGate。
- 不引入自动执行或自动批准。

## 实施步骤

1. 为 Agent Loop 新增 tool result feedback 测试。
2. 在 `_submit_tool_call()` 后写入 `tool.result.observed` trace。
3. 使用 `evidence_redactor.redact()` 对输出、错误和原因脱敏。
4. Planner 从 recent trace 提取最近工具结果摘要。
5. `run_loop()` 支持文本完成态直接结束。
6. 跑 targeted tests、full tests、quality。

## 验收标准

- 第二轮模型请求能看到第一轮工具输出。
- 明文 secret 不进入下一轮 prompt。
- 工具结果 trace 使用结构化 payload。
- 文本完成态不再被误判为 `needs_replan`。

