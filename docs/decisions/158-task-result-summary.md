# M158 Decision — Task Result Summary Live

> 基线：M157 已完成并 push（e0c57fc）。AgentLoop 只返回最后一步，TaskClosure 有丰富生命周期但无结构化结果摘要。本 milestone 补齐结构化结果摘要能力。

## 决策

**通过**。M158 已补齐结构化结果摘要能力。P1 缺口（前端无结果摘要展示）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `packages/shared/src/protocol-closure-summary.ts` | 新建 `TaskResultSummary` 接口 | P1 类型 |
| `services/agent-core/src/bolt_core/task_closure_result_summary.py` | 新建 `TaskResultSummaryBuilder` 类 | P1 后端 |
| `services/agent-core/src/bolt_core/task_closure_service.py` | 新增 `result_summary()` 方法 | P1 后端 |
| `services/agent-core/src/bolt_core/task_closure_api.py` | 新增 `GET /task-closures/{id}/result-summary` 端点 | P1 后端 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `fetchTaskResultSummary` 函数 | P1 前端 |
| `apps/desktop/src/TaskResultSummaryPanel.tsx` | 新建结果摘要展示组件 | P1 前端 |
| `apps/desktop/src/GoalConsole.tsx` | 装配 TaskResultSummaryPanel | P1 集成 |
| `services/agent-core/tests/test_task_closure_service.py` | 新增 3 个 result_summary 测试 | P1 测试 |
| `apps/desktop/src/TaskResultSummaryPanel.test.tsx` | 新建 5 个前端测试 | P2 测试 |

## 验证结果

- Backend targeted tests：3 passed（test_task_closure_service.py result_summary）
- Frontend targeted tests：5 passed（TaskResultSummaryPanel.test.tsx）
- Desktop tests：44 files / 330 tests passed（+5 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：M158 修改文件无 `ipcRenderer` / `process.` / `require` / `as any` / `unknown as` 命中

## 不做的事

- 不修改 `AgentLoop.run_loop()` 返回值结构
- 不新增后端执行引擎
- 不自动 push / release / tag / delete

## 下一步

M159 — Researcher Execution Engine： Researcher 从验证服务升级为能实际读取代码库产生研究摘要的执行引擎。
