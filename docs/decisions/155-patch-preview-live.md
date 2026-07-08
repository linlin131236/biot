# M155 Decision — Patch Preview Live

> 基线：M154 已完成并 push（a0fff37），补丁预览面板已有真实后端接入（M107 基础设施）。

## 决策

**通过**。M155 的 P2 缺口（风险解释不完整、测试覆盖不足）已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `apps/desktop/src/PatchPreviewPanel.tsx` | 新增 `RISK_EXPLANATIONS_CN` 映射，在风险标签旁显示中文风险解释 | P2 功能 |
| `services/agent-core/tests/test_patch_proposal_api.py` | 新建 5 个 patch API 集成测试（create/list/preview/404/dangerous path） | P2 测试 |
| `apps/desktop/src/PatchPreviewPanel.test.tsx` | 新增 4 个前端测试（风险解释、多文件、空 diff、无执行按钮） | P2 测试 |

## 验证结果

- Backend targeted tests：5 passed（test_patch_proposal_api.py）
- Frontend targeted tests：10 passed（PatchPreviewPanel.test.tsx）
- Desktop tests：42 files / 314 tests passed（+4 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 暴露：未命中
- PermissionGate bypass / auto-approve：未命中

## 不做的事

- `patch_proposal.py` — 补丁引擎已完整，不动
- `patch_proposal_api.py` — API 路由已完整，不动
- `harnessClientAutonomy.ts` — API 调用已完整，不动
- `PanelsSection.tsx` — 面板装配已完整，不动

## 下一步

自动进入 M156 — Approval Apply Desktop Flow。
