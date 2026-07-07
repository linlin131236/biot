# M82 Exec Plan — Planner/Builder/Reviewer Split

## 目标
建立 Planner / Builder / Reviewer 三段式工作流骨架，让任务从计划到实现到审查有清晰边界。

## 参考资料
| 文件 | 采用原则 |
|------|---------|
| `Flock架构分析——AI开发团队流水线设计.md` | 流水线即角色链、Arbiter 仲裁模式、质量门禁三关 |
| `AI工程-Phase16-多Agent与群体-深度笔记.md` | Supervisor 编排模式、角色专精、禁止越界 |
| `Hermes多Agent团队Profile搭建实战.md` | AGENTS.md 共享上下文、角色交接标准 |

## 设计决策

### 工作流状态机（9 状态）
```
planning → ready_for_build → building → ready_for_review → reviewing
                                                              ├→ approved
                                                              ├→ changes_requested → building
                                                              └→ blocked
任意状态 → failed
```

### 核心规则
- Builder 不能直接设置 approved（只有 Reviewer 可以）
- Reviewer 不能修改 Builder 输出（只能审，不能改）
- Reviewer 缺 evidence/source_refs 不能 approved
- 所有状态转移可测试
- 不执行代码，不修改文件

### 与 M81 的关系
- M81 定义角色协议（静态）
- M82 定义工作流（动态），引用 M81 角色进行状态验证

## 产出文件
- `services/agent-core/src/bolt_core/multi_agent_workflow.py`
- `services/agent-core/src/bolt_core/multi_agent_workflow_api.py`
- `services/agent-core/tests/test_multi_agent_workflow.py`
- `services/agent-core/tests/test_multi_agent_workflow_api.py`
- 修改 `app.py`
- `docs/decisions/082-planner-builder-reviewer-split.md`
- `docs/phase-82-review-gate.md`

## API 端点
- `POST /workflows` — 创建工作流
- `GET /workflows` — 列出工作流
- `GET /workflows/{id}` — 工作流详情
- `POST /workflows/{id}/planner-output` — 分配规划输出
- `POST /workflows/{id}/builder-output` — 分配构建输出
- `POST /workflows/{id}/reviewer-output` — 分配审查输出
- `GET /workflows/{id}/status-summary` — 中文状态摘要
- `POST /workflows/{id}/validate-transition` — 验证状态转移

## 验收
- happy path：Planner → Builder → Reviewer → approved
- Reviewer 发现问题：进入 changes_requested，返回 building
- Builder 不能直接设置 approved
- Reviewer 缺 evidence 不能 approved
- 所有状态转移可测试
- 不执行代码，不自动修改文件
