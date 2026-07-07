# Decision 082 — Planner/Builder/Reviewer Split

## 决策
建立 9 状态工作流状态机，约束 Planner → Builder → Reviewer 三段式协作。

## 状态设计
```
planning → ready_for_build → building → ready_for_review → reviewing
                                                              ├→ approved
                                                              ├→ changes_requested → building
                                                              └→ blocked
任意状态 → failed
```

## 理由
- Flock 流水线即角色链：每个角色完成后触发下一角色
- Phase16 Supervisor 编排模式：有明确的状态转换规则
- 状态机保证不跳步、不越权

## 关键设计决策
1. **Builder 不能 self-approve**：`assign_reviewer_output` 检查 builder_context ≠ reviewer_context
2. **Reviewer 只审不改**：审查输出不包含代码变更，只包含 verdict
3. **P1/P2 阻断 approved**：存在未修复 P1/P2 时 approved 被硬阻断
4. **changes_requested → building**：审查发现问题的修改循环
5. **状态历史可追溯**：每个转移记录在 state_history 中

## 权衡
- 纯内存模型 vs 持久化：当前阶段纯内存，M89 recovery 再考虑持久化
- 不执行代码 vs 自动执行：本模块纯状态管理，不触发任何文件修改或命令执行

## 结果
- 9 状态完整实现
- 39 tests 通过
- Builder self-approval 硬阻断
- changes_requested → building 循环验证
- 所有文案中文
