# M134 Decision: 先用安全摘要回填工具结果

## 决策

先通过 trace 中的 `tool.result.observed` 事件，把最近工具结果摘要注入 Planner 的 user prompt。

## 原因

当前架构中 Planner 只构造 system/user 两条消息，尚未维护完整 OpenAI tool role 对话历史。直接大改消息协议会影响面广，容易同时碰到权限、审计、任务闭环和测试稳定性。

用结构化 trace 作为中间层可以在最小范围内解决真实闭环问题：

- 工具结果可被下一轮模型看到。
- 输出进入 prompt 前可统一脱敏和截断。
- 保持现有 PermissionGate 和 trace 体系。

## 取舍

- 这还不是最终的原生 tool-message loop；M134 是安全且可验证的过渡闭环。
- 后续可以在此基础上升级为完整 messages history。

## 风险

- 大输出只截断前 2000 字符，后续如果需要更强上下文选择，需要接入 Context Lakehouse/Code Map。
- Planner prompt 中的摘要格式仍是文本，模型供应商不同可能需要调优。

