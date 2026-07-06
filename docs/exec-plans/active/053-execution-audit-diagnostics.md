# M53 Execution Audit Consistency Diagnostics

## 验收标准
- 后端提供只读诊断能力，发现 execution queue / handoff / permission / closure evidence 间的不一致。
- 诊断覆盖：waiting_permission 但无 pending、handoff completed 但 queue 未 completed、handoff failed/rejected 但 queue 未 failed、verification_command completed 但 closure.commands 缺证据、queue 指向不存在 closure、handoff 指向不存在 queue item、同一 queue item 多个 open handoff、permission_request_id 绑定不到 handoff。
- 正常 M50/M52 链路诊断结果为空。
- API 返回稳定中文严重级别：阻断、警告、提示。
- Desktop 只读展示诊断结果，不提供 auto-fix 按钮。

## 最小边界
- 只读取 queue、handoff、PermissionQueue、closure。
- 不自动修复，不自动执行，不新增 approve/reject/request-permission 能力。
- UI 只显示问题、摘要和建议人工处理。

## 验证
- 后端单元测试覆盖每种不一致 fixture 和正常链路为空。
- API 测试覆盖中文字段稳定。
- Desktop vitest 覆盖只读展示，且不出现能力按钮。
