# M167 Self-Review Auto-Fix 执行计划

## 目标

为 Reviewer 的低风险发现提供自动修复提案能力，但不直接写入文件。

## 验收标准

- P0/P1/security findings 保留为人工处理。
- P2 低风险文档/格式类发现可生成提案。
- API 返回 fixed/remaining/fixed_items/remaining_items/proposed_code。
- 桌面面板中文展示结果。
- targeted tests、quality、Chinese UI、diff check 通过。

## 风险

- Auto-fix 不能自动改业务代码。
- 不能把安全问题降级成自动修复。
