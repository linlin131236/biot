# M160 Decision — Builder Execution Engine

> 基线：M159 已完成并 push（7dc2bef）。Builder 只有协议契约（BuilderOutput dataclass），没有执行引擎。本 milestone 升级为能实际产生代码变更提案的执行引擎。

## 决策

**通过**。M160 已补齐 Builder 执行引擎。P1 缺口（Builder 不执行任务）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/builder_engine.py` | 新建 BuilderEngine 执行引擎 | P1 后端 |
| `services/agent-core/src/bolt_core/builder_api.py` | 新建 `POST /builder/execute` 端点 | P1 后端 |
| `services/agent-core/src/bolt_core/app.py` | 注册 builder router | 集成 |
| `apps/desktop/src/BuilderPanel.tsx` | 新建构建引擎面板 | P1 前端 |
| `apps/desktop/src/BuilderPanel.test.tsx` | 新建 5 个前端测试 | P2 测试 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `executeBuilderTask`、`fetchBuilderProposals` | P1 前端 |
| `apps/desktop/src/panelsApi.ts` | 新增 builder namespace | 集成 |
| `apps/desktop/src/PanelsSection.tsx` | 装配 BuilderPanel | 集成 |
| `services/agent-core/tests/test_builder_engine.py` | 新建 6 个后端测试 | P1 测试 |
| `apps/desktop/src/App.test.tsx` | 修复工作区文本匹配 | 测试修复 |
| `apps/desktop/src/uiWorkflowDogfood.test.tsx` | 修复工作区文本匹配 | 测试修复 |

## 验证结果

- Backend targeted tests：6 passed（test_builder_engine.py）
- Frontend targeted tests：5 passed（BuilderPanel.test.tsx）
- Desktop tests：46 files / 341 tests passed（+5 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 安全扫描：未命中

## 不做的事

- 不直接写文件（只 produce proposals）
- 不自我审批
- 不绕过 PermissionGate
- 不自动 push / release / tag / delete

## 下一步

M161 — Reviewer Execution Engine + strict Gate：Reviewer 从 gate 逻辑升级为能实际读取 Builder 输出产生审查发现的执行引擎。
