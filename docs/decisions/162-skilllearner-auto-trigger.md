# M162 Decision — SkillLearner Auto-Trigger

> 基线：M161 已完成并 push（fda3707）。SkillLearner 只有被动触发（record_failure 手动记录后 analyze），没有主动扫描能力。本 milestone 升级为主动扫描失败记忆。

## 决策

**通过**。M162 已补齐 SkillLearner 主动扫描能力。P2 缺口（SkillLearner 不主动扫描）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/skilllearner_review_loop.py` | 新增 `auto_scan()` 方法 | P2 后端 |
| `services/agent-core/src/bolt_core/skilllearner_review_loop_api.py` | 新增 `POST /skill-learner/auto-scan` 端点 | P2 后端 |
| `apps/desktop/src/SkillLearnerPanel.tsx` | 新增自动扫描 UI | P2 前端 |
| `apps/desktop/src/SkillLearnerPanel.test.tsx` | 新增 8 个前端测试 | P2 测试 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `autoScanSkillLearner`、`recordFailure` | P2 前端 |
| `apps/desktop/src/panelsApi.ts` | 新增 skilllearner namespace | 集成 |
| `apps/desktop/src/PanelsSection.tsx` | 装配 SkillLearnerPanel | 集成 |
| `services/agent-core/tests/test_skilllearner_auto_scan.py` | 新建 4 个后端测试 | P2 测试 |

## 验证结果

- Backend targeted tests：4 passed（test_skilllearner_auto_scan.py）
- Frontend targeted tests：8 passed（SkillLearnerPanel.test.tsx）
- Desktop tests：48 files / 355 tests passed（+8 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：未命中

## 不做的事

- 不修改业务代码
- 不修改 skill 文件
- 不自动审批
- 不自动 push / release / tag / delete

## 下一步

M163 — Orchestrator core (5 roles wired)：串联 Planner → Researcher → Builder → Reviewer → SkillLearner。
