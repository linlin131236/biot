# M69 Long Task Recovery Dogfood — 执行计划

## 目标
把 M61-M68 串起来做长任务恢复 dogfood，重点验证状态、暂停、恢复、steering、预算、失败分类、重试建议能形成安全闭环。不新增自动执行器。

## 参考资料
| # | 文件 | 采用原则 |
|---|------|---------|
| 1 | `AI工程-Phase14-Agent工程-深度笔记-上.md` | Lesson 01：停止条件、轮次预算；Lesson 03：Reflexion 反思模式——失败后写反思 |
| 2 | `AI工程-Phase14-Agent工程-深度笔记-下.md` | Lesson 26：五种高频失败模式 + 级联错误是杀手——dogfood 必须覆盖 |
| 3 | `20260628_AgentHarness20层进化指南.md` | s11 错误恢复三段论；s03 权限三道闸门——dogfood 必须验证 |

## 范围
- 新增 `LongTaskRecoveryDogfoodService`：只读 readiness 检查
- 检查项：task graph、state machine、pause/resume、steering、budget、failure classifier、retry loop、PermissionGate、traceability
- 新增 API：`GET /dogfood/long-task-recovery`
- 新增 `docs/phase-69-review-gate.md`
- **不新增自动执行器**

## 产出文件
- `services/agent-core/src/bolt_core/long_task_recovery_dogfood.py`
- `services/agent-core/src/bolt_core/long_task_recovery_dogfood_api.py`
- `services/agent-core/tests/test_long_task_recovery_dogfood.py`
- `docs/exec-plans/active/069-long-task-recovery-dogfood.md`
- `docs/decisions/069-long-task-recovery-dogfood.md`
- `docs/phase-69-review-gate.md`

## 验收标准
- [ ] dogfood 检查 9 项全部可执行
- [ ] happy path 通过（模拟合规场景）
- [ ] 至少一个失败路径能给中文原因
- [ ] 不新增 shell、push、release、tag、delete、approve 自动入口
- [ ] targeted tests 完整
