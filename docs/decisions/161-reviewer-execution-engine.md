# M161 Decision — Reviewer Execution Engine + strict Gate

> 基线：M160 已完成并 push（771e8af）。Reviewer 只有 gate 逻辑（ReviewerIndependentGateService 验证预计算的 review package），没有执行引擎。本 milestone 升级为能实际读取 Builder 输出产生审查发现的执行引擎。

## 决策

**通过**。M161 已补齐 Reviewer 执行引擎 + strict Gate。P1 缺口（Reviewer 不执行审查）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/reviewer_engine.py` | 新建 ReviewerEngine 执行引擎 | P1 后端 |
| `services/agent-core/src/bolt_core/reviewer_api.py` | 新建 `POST /reviewer/review` 端点 | P1 后端 |
| `services/agent-core/src/bolt_core/app.py` | 注册 reviewer router | 集成 |
| `apps/desktop/src/ReviewerPanel.tsx` | 新建审查引擎面板 | P1 前端 |
| `apps/desktop/src/ReviewerPanel.test.tsx` | 新建 6 个前端测试 | P2 测试 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `reviewBuilderOutput`、`fetchReviewVerdictLabel` | P1 前端 |
| `apps/desktop/src/panelsApi.ts` | 新增 reviewer namespace | 集成 |
| `apps/desktop/src/PanelsSection.tsx` | 装配 ReviewerPanel | 集成 |
| `services/agent-core/tests/test_reviewer_engine.py` | 新建 7 个后端测试 | P1 测试 |

## 验证结果

- Backend targeted tests：7 passed（test_reviewer_engine.py）
- Frontend targeted tests：6 passed（ReviewerPanel.test.tsx）
- Desktop tests：47 files / 347 tests passed（+6 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：未命中

## 不做的事

- 不修改 Builder 输出
- 不执行工具
- 不自我审批
- 不自动 push / release / tag / delete

## 下一步

M162 — SkillLearner Auto-Trigger：SkillLearner 从被动触发升级为主动扫描失败模式。
