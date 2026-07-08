# M154 Decision — Audit Timeline Live

> 基线：M153 已完成并 push（b2a5cd1），审计时间线面板已有真实后端接入（M93 基础设施）。

## 决策

**通过**。M154 的 P1 安全缺口（事件摘要未完全脱敏）和 P2 功能缺口（无类型筛选）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/execution_audit_timeline.py` | queue item title/reason/result 摘要应用 `redact()` | P1 安全修复 |
| `services/agent-core/src/bolt_core/audit_timeline_api.py` | `/audit-timeline` 端点新增 `source` 查询参数，支持按事件来源筛选 | P2 功能 |
| `apps/desktop/src/harnessClientAutonomy.ts` | `fetchAuditTimeline` 新增 `source` 参数 | P2 功能 |
| `apps/desktop/src/AuditTimelinePanel.tsx` | 新增类型筛选按钮组（全部/执行队列/人工交接/任务闭环/权限审批） | P2 功能 |
| `services/agent-core/tests/test_execution_audit_timeline.py` | 新增 3 个脱敏测试（title/reason/result） | P1 测试 |
| `services/agent-core/tests/test_execution_audit_timeline_api.py` | 新增 2 个 source filter 集成测试（queue/handoff） | P2 测试 |
| `apps/desktop/src/AuditTimelinePanel.test.tsx` | 新增 3 个前端测试（筛选按钮、筛选隐藏、脱敏不暴露） | P2 测试 |

## 验证结果

- Backend targeted tests：11 passed（test_execution_audit_timeline.py 6 + test_execution_audit_timeline_api.py 5）
- Frontend targeted tests：9 passed（AuditTimelinePanel.test.tsx）
- Desktop tests：42 files / 310 tests passed（+3 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 暴露：未命中
- PermissionGate bypass / auto-approve：未命中

## 不做的事

- `execution_audit_timeline_api.py` 未改动（路由逻辑已完整）
- `PanelsSection.tsx` 未改动（AuditTimelinePanel 已接入）
- `permission_center.py` 未改动（M153 已完成）

## 下一步

自动进入 M155 — Patch Preview Live。
