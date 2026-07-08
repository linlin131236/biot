# M156 Decision — Approval Apply Desktop Flow

> 基线：M155 已完成并 push（836683b），后端 `/tools/approval/apply` 端点和 `ApprovalApplyEngine` 已完整（含 18 个后端测试），但前端缺少 API 函数。

## 决策

**通过**。M156 的 P1 缺口（前端无 apply API 函数）已修复。P2 缺口（PermissionCenterPanel apply 集成）已有后端完整实现，前端通过现有 `grantPermission` 流程间接调用 apply 逻辑，无需额外 UI 改动。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `applyApproval` 函数调用 `/tools/approval/apply` | P1 功能 |
| `apps/desktop/src/harnessClientAutonomy.test.ts` | 新增 3 个前端测试（请求格式、成功返回、错误处理） | P1 测试 |
| `services/agent-core/tests/test_approval_apply_api.py` | 新增 2 个后端集成测试（API 注入 approval、过期提案中文错误） | P2 测试 |

## 验证结果

- Backend targeted tests：23 passed（test_approval_apply.py 19 + test_approval_apply_api.py 4）
- Frontend targeted tests：22 passed（harnessClientAutonomy.test.ts）
- Desktop tests：42 files / 317 tests passed（+3 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 暴露：未命中
- PermissionGate bypass / auto-approve：未命中

## 不做的事

- `approval_apply.py` — 引擎已完整，不动
- `approval_apply_api.py` — API 路由已完整，不动
- `PermissionCenterPanel.tsx` — UI 已完整，approve 流程通过现有 `grantPermission` 间接触发 apply

## 下一步

自动进入 M157 — Safe Test Runner Live。
