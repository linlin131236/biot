# M163 Decision — Orchestrator Core (5 Roles Wired)

> 基线：M162 已完成并 push（e17c9cf）。5 个角色各自已有执行引擎，但没有编排器串联。本 milestone 创建 Orchestrator 核心串联 5 角色。

## 决策

**通过**。M163 已创建 OrchestratorEngine 串联 5 角色。P1 缺口（无编排器）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/orchestrator_engine.py` | 新建 OrchestratorEngine | P1 后端 |
| `services/agent-core/src/bolt_core/orchestrator_api.py` | 新建 `POST /orchestrator/run` + `GET /orchestrator/roles` | P1 后端 |
| `services/agent-core/src/bolt_core/app.py` | 注册 orchestrator router | 集成 |
| `apps/desktop/src/OrchestratorPanel.tsx` | 新建编排器面板 | P1 前端 |
| `apps/desktop/src/OrchestratorPanel.test.tsx` | 新建 6 个前端测试 | P2 测试 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `runOrchestrator`、`fetchOrchestratorRoles` | P1 前端 |
| `apps/desktop/src/panelsApi.ts` | 新增 orchestrator namespace | 集成 |
| `apps/desktop/src/PanelsSection.tsx` | 装配 OrchestratorPanel | 集成 |
| `services/agent-core/tests/test_orchestrator_engine.py` | 新建 6 个后端测试 | P1 测试 |

## 验证结果

- Backend targeted tests：6 passed（test_orchestrator_engine.py）
- Frontend targeted tests：6 passed（OrchestratorPanel.test.tsx）
- Desktop tests：49 files / 361 tests passed（+6 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：未命中

## 不做的事

- 不直接写文件
- 不自动审批
- 不绕过 PermissionGate
- 不自动 push / release / tag / delete

## 下一步

M164 — Sleep/Wake mode：空闲循环 + 目标唤醒。
