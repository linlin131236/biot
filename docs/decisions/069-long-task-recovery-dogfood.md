# M69 Long Task Recovery Dogfood — 设计决策

## 决策背景
M61-M68 已各自通过独立测试，但尚未验证它们在一起能形成安全闭环。M69 作为 dogfood/readiness milestone，只读检查整体闭环是否完整，不新增执行逻辑。

## 决策 1：只读 readiness，不是自动执行器
**选择**：`LongTaskRecoveryDogfoodService` 只做检查、返回报告，不执行任何恢复操作。

**理由**：
- 文档明确："这是 dogfood/readiness，不是自动执行器"
- 恢复操作应是人工决策的结果，不是自动触发
- 对齐 `ReleaseReadinessService` 的只读模式

## 决策 2：9 项检查覆盖 M61-M68 关键路径
**选择**：每项检查对应一个已完成的 milestone 能力，验证其存在且安全。

检查项：
1. task_graph_exists — M61 Planner Task Graph
2. state_machine_valid — M62 Execution State Machine
3. pause_resume_verifies_permissions — M66 Pause/Resume
4. steering_no_direct_execution — M67 Human Steering
5. budget_blocks_on_exceed — M68 Budget Controls
6. failure_classifier_chinese_diagnosis — M64 Failure Classification
7. retry_loop_no_dangerous_retry — M65 Safe Retry Loop
8. permission_gate_not_bypassed — 安全底座
9. trace_evidence_traceable — 审计/证据链

## 决策 3：服务级自检，不依赖运行中的 agent
**选择**：dogfood 检查的是"这些能力是否存在且配置正确"，不是"当前是否有一个正在运行的 agent"。

**理由**：
- 可在任意时刻运行，不要求 agent 处于特定状态
- 适合 CI/CD 和 review gate 场景
- 不引入时序依赖

## 风险
- dogfood 检查较浅（存在性检查），不深入验证每个组件边界条件（由各自 targeted tests 覆盖）
- 这是一个 readiness gate，不是 E2E 测试套件
