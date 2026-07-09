# M170 E2E Autonomous Loop 执行计划

## 目标

提供端到端自主循环诊断闭环：Planner、Researcher、Builder、Reviewer 的状态可被汇总展示。

## 验收标准

- `/orchestrator/autonomous-loop` 返回 status、verdict、rounds_completed、trace。
- max_rounds 被限制在 1-5。
- Gate 冻结时拒绝启动自主循环。
- 不执行 push/release/tag/delete，不自动批准权限。
- 桌面面板中文展示循环结果。
- targeted tests、quality、Chinese UI、diff check 通过。

## 风险

- 本阶段是受限诊断闭环，不把高风险写入纳入自动执行。
- 若发现 Gate 或权限边界被绕过，必须停止并修复。
