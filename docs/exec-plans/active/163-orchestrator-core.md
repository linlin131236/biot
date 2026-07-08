# M163 Exec Plan — Orchestrator Core (5 Roles Wired)

> 当前基线：M162 已完成并 push（e17c9cf）。5 个角色（Planner/Researcher/Builder/Reviewer/SkillLearner）各自已有执行引擎，但没有编排器串联它们。本 milestone 创建 Orchestrator 核心。

## 现状分析

### 已有
- `Planner`：构建 ModelRequest（planner.py）
- `ResearcherEngine`：查询数据源产生研究摘要（researcher_engine.py）
- `BuilderEngine`：产生代码变更提案（builder_engine.py）
- `ReviewerEngine`：审查 Builder 输出，strict Gate（reviewer_engine.py）
- `SkillLearnerReviewLoopService`：分析失败模式，生成改进提案（skilllearner_review_loop.py）

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 无编排器 | P1 | 5 个角色各自独立，没有串联执行 |
| 无角色流转 | P1 | blocked → loop back 到 Builder 的逻辑缺失 |
| 无 orchestrate endpoint | P1 | 没有 `POST /orchestrator/run` |
| 无前端 OrchestratorPanel | P2 | 桌面端无编排器面板 |

## 执行方案

### 改动 1：OrchestratorEngine
**文件**：`services/agent-core/src/bolt_core/orchestrator_engine.py`（新建）

```python
class OrchestratorEngine:
    def __init__(self, planner, researcher, builder, reviewer, skill_learner):
        self._planner = planner
        self._researcher = researcher
        self._builder = builder
        self._reviewer = reviewer
        self._skill_learner = skill_learner

    def orchestrate(self, task_description: str, workspace: str) -> OrchestrationResult:
        # 1. Planner: produce plan
        # 2. Researcher: research if needed
        # 3. Builder: produce code changes
        # 4. Reviewer: review (strict gate)
        # 5. If blocked → loop back to Builder (max 3 rounds)
        # 6. If approved → SkillLearner: analyze
        # 7. Return OrchestrationResult
```

约束：
- 最多 3 轮 review loop（blocked → builder → reviewer）
- 不直接写文件（builder 只 produce proposals）
- 不自动审批
- 不绕过 PermissionGate

### 改动 2：后端 endpoint
**文件**：`services/agent-core/src/bolt_core/orchestrator_api.py`（新建）

`POST /orchestrator/run` - 接收 task_description + workspace，返回 OrchestrationResult

### 改动 3：前端
- `harnessClientAutonomy.ts`：`runOrchestrator`
- `OrchestratorPanel.tsx`：任务输入、执行按钮、5 角色流转展示
- `OrchestratorPanel.test.tsx`：测试

## 验收标准
1. ✅ OrchestratorEngine 串联 5 个角色
2. ✅ blocked → loop back to Builder（max 3 rounds）
3. ✅ 所有 UI 文案中文
4. ✅ `pnpm run quality` 通过
5. ✅ `git diff --check` 通过
6. ✅ 无 `as any` / `unknown as`
7. ✅ renderer 无危险暴露
