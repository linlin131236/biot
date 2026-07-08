# M155 Exec Plan — Patch Preview Live：补丁预览真实接入

> 当前基线：M154 已完成并 push（a0fff37），补丁预览面板已有真实后端接入（M107 基础设施），但风险解释不完整、测试覆盖不足。
> 本 milestone 补齐中文风险解释和测试覆盖。

---

## 参考资料

本次开工前实际读取 3 篇 BinCloud 资料：

1. `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`
   - 采用原则：工具调用日志必须脱敏；敏感信息自动过滤；最小权限原则。
   - 落点：补丁 diff 中可能包含敏感文件路径或代码，需确保路径安全。

2. `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md`
   - 采用原则：用户第一屏应该是可用工作台，所有状态必须能解释下一步，中文 UI。
   - 落点：补丁预览的风险等级必须有中文解释，用户能理解为什么是高风险。

3. `E:\BinCloud\知识库\03-知识\AI工程\AI安全与对齐全景.md`
   - 采用原则：工具链数据流安全；证据脱敏防止 token/key 泄露。
   - 落点：补丁 diff 预览只读，不执行，不自动应用。

---

## 现状分析

### 已有（M107 基础设施）
- 后端：`patch_proposal_api.py` — `/tools/patch/create`、`/tools/patch/list`、`/tools/patch/{id}`、`/tools/patch/{id}/preview` 端点已完整
- 后端：`patch_proposal.py` — `PatchProposalEngine` 支持多文件、unified diff、风险评估、路径安全检查（`.claude`/`.bolt`/`.git` 等阻断）
- 前端：`PatchPreviewPanel.tsx` — 已接入真实 API（`fetchPatchList`、`fetchPatchPreview`），有文件列表、diff 预览、风险标签、空状态、错误状态
- 前端：`PanelsSection.tsx` — `PatchPreviewPanel` 已装配，props 类型已完整
- 测试：`PatchPreviewPanel.test.tsx`（6 个前端测试）、`test_patch_proposal.py`（后端测试）

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 风险解释不完整 | P2 | 前端 `risk_label` 仅显示"低/中/高"，缺少完整中文风险解释（如"此操作可能修改多个文件，建议仔细审查 diff"） |
| 前端测试覆盖不足 | P2 | 现有 6 个测试未覆盖多文件、危险路径、空 diff、格式错误、中文 UI |
| 后端 patch API 无集成测试 | P2 | `test_patch_proposal_api.py` 不存在，缺少端点级测试 |

---

## 执行方案

### 改动 1：前端中文风险解释（P2）

**文件**：`apps/desktop/src/PatchPreviewPanel.tsx`

**操作**：
在组件内添加 `RISK_EXPLANATIONS_CN` 映射：
```typescript
const RISK_EXPLANATIONS_CN: Record<string, string> = {
  low: '此补丁仅涉及少量文件，风险较低。',
  medium: '此补丁涉及多个文件或敏感操作，建议仔细审查 diff。',
  high: '此补丁涉及大量文件变更或危险操作，建议逐行审查后再批准。',
  critical: '此补丁涉及核心文件或破坏性操作，需极度谨慎。',
};
```

在风险标签旁显示解释文本（类似权限中心的 `risk_explanation_cn`）。

### 改动 2：后端 patch API 集成测试（P2）

**文件**：`services/agent-core/tests/test_patch_proposal_api.py`（新建）

**新增测试**：
1. `test_create_patch_returns_validation` — POST `/tools/patch/create` 返回有效补丁
2. `test_list_patches_returns_empty_initially` — GET `/tools/patch/list` 初始为空
3. `test_preview_patch_returns_diff` — GET `/tools/patch/{id}/preview` 返回 unified_diff
4. `test_preview_missing_patch_returns_404` — GET `/tools/patch/{id}/preview` 不存在的补丁返回 404
5. `test_create_patch_blocks_dangerous_paths` — `.claude` 目录下的文件被拒绝

### 改动 3：前端补充测试（P2）

**文件**：`apps/desktop/src/PatchPreviewPanel.test.tsx`

**新增测试**：
1. `test_multi_file_patch_shows_all_files` — 多文件补丁显示所有文件路径
2. `test_dangerous_path_shows_blocked_warning` — 危险路径在文件列表中标记
3. `test_empty_diff_does_not_render_preview` — 空 diff 不渲染 diff 预览区
4. `test_format_error_shows_error_state` — 格式错误显示错误状态
5. `test_chinese_risk_explanation_displayed` — 中文风险解释文本显示

---

## 验收标准

1. ✅ 展示真实多文件 unified diff（已有，不动）。
2. ✅ 支持文件列表、增删行统计、风险提示（已有，不动）。
3. ✅ 只预览，不写入（已有，不动）。
4. ✅ 多文件 diff 不串改（已有，不动）。
5. ✅ 显示中文风险解释（新增）。
6. ✅ targeted tests 覆盖多文件、危险路径、空 diff、格式错误、中文 UI。
7. ✅ 所有 UI 文案中文。
8. ✅ `pnpm run quality` 通过。
9. ✅ `git diff --check` 通过。
10. ✅ renderer 无危险暴露（PatchPreviewPanel 不改动 renderer 相关代码）。
11. ✅ 无 `as any` / `unknown as`。
12. ✅ 无私人称呼。

---

## 实施顺序

1. 前端中文风险解释（`PatchPreviewPanel.tsx`）
2. 后端 patch API 集成测试（`test_patch_proposal_api.py`）
3. 前端补充测试（`PatchPreviewPanel.test.tsx`）
4. 运行 targeted tests
5. 运行 full quality gates
6. 写 decision + review gate + project-state 更新
7. commit

---

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 风险解释文本过长影响 UI | 低 | 使用小字号（12px）和灰色文字，与现有 disclaimer 样式一致 |
| 多文件 diff 渲染性能 | 低 | `<pre>` 块已有 `maxHeight: 300` 和 `overflow: 'auto'`，大量 diff 可滚动 |
| 后端集成测试需要 fixture | 低 | 使用 `create_patch` 端点动态创建补丁，无需文件系统 fixture |

---

## 不改动的部分

- `patch_proposal.py` — 补丁引擎已完整，不动
- `patch_proposal_api.py` — API 路由已完整，不动
- `harnessClientAutonomy.ts` — API 调用已完整，不动
- `PanelsSection.tsx` — 面板装配已完整，不动
