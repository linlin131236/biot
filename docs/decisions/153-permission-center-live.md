# M153 Decision — Permission Center Live

> 基线：M152 已完成并 push，权限中心面板已有真实后端接入（M92 基础设施）。

## 决策

**通过**。M153 的 P1 安全缺口已修复，P2 测试覆盖已补齐。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/permission_center.py` | 导入 `redact()` 并应用于 `payload_summary` | P1 安全修复 |
| `services/agent-core/tests/test_permission_center.py` | 新增 3 个脱敏测试（API key inline、TOKEN inline、Bearer） | P2 测试覆盖 |
| `apps/desktop/src/PermissionCenterPanel.test.tsx` | 新增 1 个前端测试验证 UI 不显示原始 key | P2 测试覆盖 |

## 验证结果

- Backend targeted tests：17 passed（含 3 个新脱敏测试）
- Frontend targeted tests：11 passed（含 1 个新脱敏测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 暴露：未命中
- PermissionGate bypass / auto-approve：未命中

## 不做的事

- `PermissionCenterPanel.tsx` 未改动（UI 已完整，后端脱敏后前端自然展示脱敏数据）
- `permission_center_api.py` 未改动（路由已完整）
- `harnessClient.ts` / `PanelsSection.tsx` 未改动（API 绑定已完整）

## 下一步

自动进入 M154 — Audit Timeline Live。
