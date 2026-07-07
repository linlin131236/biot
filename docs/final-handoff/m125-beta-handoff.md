# Biot M125 Beta Handoff

## 当前边界
Biot 已从 M55 推进到 M125，形成安全执行、审计、恢复、记忆、多 Agent、中文 UI、工具生态、智能评估和 Beta 可靠性门禁。

## 能力概览
- 安全底座：PermissionGate、证据脱敏、审计完整性、发布准备度。
- Agent 工作流：任务图、状态机、工具选择、失败分类、安全重试、暂停恢复、人类 steering。
- 上下文与记忆：Project Profile、Code Map、Decision/Failure/User Preference Memory、Context Compaction、Thread Handoff。
- 多 Agent：角色协议、Planner/Builder/Reviewer、Researcher、SkillLearner、团队状态和恢复。
- 中文桌面：任务首页、权限中心、审计时间线、诊断、发布准备、多任务、失败解释、会话恢复、设置。
- 工具生态：工具注册、manifest、权限契约、只读运行器、写入提案、补丁预览、批准后 apply、安全测试运行器。
- 智能评估：工具调用、补丁应用、失败诊断、权限边界、多 Agent 协作、记忆检索、中文交互、E2E 和失败恢复 dogfood。
- Beta 可靠性：崩溃恢复、数据迁移、升级回滚、隐私安全、公开 Beta readiness。

## 不做的事
- 不自动 push/release/tag/delete。
- 不自动批准权限。
- 不绕过 PermissionGate。
- 不把 J-lens 或内部意图信号当作执行授权。
- 不自动迁移真实数据。

## 已知风险
- 部分多 Agent 与 Task Graph 仍是内存模型，未来可评估持久化。
- API 全量测试耗时较长。
- 部分历史文件有 size gate 豁免，后续可专项拆分。

## 接手建议
新窗口先读 `docs/project-state.md`、`docs/phase-125-review-gate.md`、路线图和知识索引，再根据爸爸授权决定是否 push 或进入后续 M126+。
