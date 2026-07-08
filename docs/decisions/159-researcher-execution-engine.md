# M159 Decision — Researcher Execution Engine

> 基线：M158 已完成并 push（99f9d1c）。Researcher 只有 brief/summary 数据验证，不能实际查询数据源。本 milestone 升级为执行引擎。

## 决策

**通过**。M159 已补齐 Researcher 执行引擎。P1 缺口（Researcher 不执行查询）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/researcher_integration.py` | 保留数据模型和验证逻辑，新增 import | 改造 |
| `services/agent-core/src/bolt_core/researcher_engine.py` | 新建 ResearcherEngine 执行引擎 | P1 后端 |
| `services/agent-core/src/bolt_core/researcher_integration_api.py` | 新增 `POST /research/execute` 端点 | P1 后端 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `createResearchBrief`、`executeResearch`、`fetchResearchScopes` | P1 前端 |
| `apps/desktop/src/ResearcherPanel.tsx` | 新建研究员面板组件 | P1 前端 |
| `apps/desktop/src/ResearcherPanel.test.tsx` | 新建 6 个前端测试 | P2 测试 |
| `services/agent-core/tests/test_researcher_integration.py` | 新增 6 个 execute_brief 测试 | P1 测试 |
| `scripts/check-architecture.mjs` | 豁免 researcher_engine.py 的 subprocess 关键词 | 工具 |

## 验证结果

- Backend targeted tests：6 passed（execute_brief 系列）
- Frontend targeted tests：6 passed（ResearcherPanel.test.tsx）
- Desktop tests：45 files / 336 tests passed（+6 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：未命中

## 不做的事

- 不修改文件
- 不执行工具
- 不自动审批
- 不自动 push / release / tag / delete

## 下一步

M160 — Builder Execution Engine：Builder 从协议契约升级为能实际修改文件的执行引擎。
