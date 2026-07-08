# M126-M130 Product Workbench Implementation Plan

## Goal

把 M91-M125 已经完成的任务首页、补丁预览、批准 apply、白名单测试、失败解释、恢复建议和审计能力，收束成一个爸爸能直接理解的中文桌面工作流。

## References

- `Agent产品化流水线.md`：串行契约优先，先让需求、计划、实现、验证、复盘成为稳定流水线。
- `20260628_讨论场到执行系统_ZCode看板法.md`：每个任务要有目标、状态、验收标准和下一步。
- `OpenClaw实际场景学习报告.md`：项目状态、心跳、检查清单和可见恢复路径要优先产品化。

## Milestones

1. M126 Real Agent Workbench
   - 新增只读 `/product-workbench`。
   - 新增 `ProductWorkbenchPanel`。
   - 串起“用户意图 -> 计划 -> 读取上下文 -> 补丁预览 -> 人工批准 -> apply -> 测试 -> 审计恢复”。

2. M127 Patch Approval Lane
   - 在工作台突出补丁风险、批准边界和 apply 前检查。
   - 不新增自动批准或自动 apply。

3. M128 Test Feedback Lane
   - 在工作台展示白名单测试能力和测试回填状态。
   - 不允许任意 shell。

4. M129 Failure And Recovery Lane
   - 在工作台展示失败解释、重试风险和恢复前检查。
   - 不自动 retry，不自动 fix。

5. M130 Product Workbench Dogfood
   - 增加 dogfood gate，验证 M126-M129 桌面工作流可见、安全、中文、只读。
   - 全量质量门通过后停止，不进入 M131。

## Verification

- Targeted backend tests。
- Targeted desktop tests。
- Shared/desktop/full backend tests。
- `pnpm run quality`。
- `git diff --check`。
- `node scripts/check-docs.mjs`。
- `node scripts/check-chinese-ui.mjs`。
- `as any` / `unknown as` 扫描。
- renderer 暴露扫描。
- 自动 push/release/tag/delete/approve 扫描。

