# M67 Human Steering — 设计决策

## 决策背景
Biot V2 Agent 工作流核心（M61-M66）已建立：Task Graph、State Machine、Tool Selection、Failure Classification、Safe Retry、Pause/Resume。但缺少用户在任务运行中安全介入的能力。M67 补齐这一环：允许用户转向、补充、暂停、要求复查，但绝不绕过安全边界。

## 决策 1：关键词分类 vs LLM 分类
**选择**：关键词匹配分类。

**理由**：
- 确定性：不依赖模型可用性，离线可测试
- 安全：不会因 prompt injection 被诱导分类错误
- 成本：零 token 消耗
- 降级：unknown 返回中文说明，引导用户明确表达

**拒绝**：LLM 分类 — 引入不可控推理，增加安全面。

## 决策 2：副作用 steering 只生成 pending
**选择**：change_goal 和 abort 只记录 pending 建议，返回 requires_human_confirmation=true。

**理由**：
- change_goal：修改目标涉及权限和范围变更，必须人工二次确认
- abort：终止进程可能丢失数据，必须人工二次确认
- 对齐 Harness s03 权限原则：白名单→规则→用户确认

**拒绝**：直接执行 — 违反安全边界。

## 决策 3：pause 走 M66 完整路径
**选择**：pause steering 委托给 M66 PauseResumeService。

**理由**：
- 复用已有快照机制
- 复用三重安全检查
- 复用权限复查强制执行
- 不引入第二条暂停路径

## 决策 4：evidence 记录到 conversation store + trace log
**选择**：双写 conversation store（metadata 带 steering 标记）+ trace log。

**理由**：
- conversation store：按时间线可检索
- trace log：按 run 可审计
- 对齐文档要求的"steering 应能进入 timeline / conversation / audit 中至少一种可验证证据"

## 决策 5：不接前端改动
**选择**：本 milestone 只做后端 service + API。

**理由**：
- 前端 SideChatPanel 已有 `SteeringResult` 接口和 `steerRun` 调用
- 后端增强后前端自然受益，不需要改 UI
- 减少范围，聚焦核心安全逻辑

## 风险
- 关键词分类可能漏判边缘表达 → unknown 降级 + 中文引导足够
- 前端 SteeringResult 类型太简单（只有 status）→ 暂不扩展 shared 类型，API 返回的额外字段前端可选择性消费
