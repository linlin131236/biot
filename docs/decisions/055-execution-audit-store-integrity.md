# M55 Decision: Execution Audit Store Integrity Guard

## 决策
新增只读 integrity service，复用 ExecutionAuditStore 的 load() 方法读取文件，对读取结果进行结构化校验。不修改 store 自身的 write 逻辑，因为 store 已经通过"load-modify-save"模式保证了 queue/handoff/closure 互不覆盖。

## 备选方案与排除
- **在 store._save 中写 hash**：排除。增加复杂度且不解决已有损坏文件的诊断需求。store 的 atomic write（tmp + os.replace）已经防止半写入破坏。
- **定时后台扫描**：排除。不新增自动执行。
- **自动修复**：排除。违反"不自动修复"原则。

## 设计
- `ExecutionAuditIntegrityService` 仅依赖 `ExecutionAuditStore`
- 方法 `list_integrity()` 返回诊断列表，完全复用 diagnostics 的 severity/severity_label 模式
- API 端点 GET `/execution-audit/integrity` 只读
- UI 复用 ExecutionHandoffPanel 中的 Diagnostics 子组件模式，新增 Integrity 子组件

## 检查项
| 场景 | 预期结果 |
|---|---|
| 文件不存在 | 返回空列表（healthy） |
| JSON 损坏 | 返回 blocking 诊断，中文提示 |
| queue_items 不是 list | 返回 blocking 诊断 |
| handoff_records 不是 list | 返回 blocking 诊断 |
| closure_records 不是 list | 返回 blocking 诊断 |
| 所有字段正常 | 返回 clean（空列表或 info 级别） |
| save_queue 后 handoff/closure 还在 | 测试确认 store 行为正确 |
| save_handoff 后 queue/closure 还在 | 测试确认 store 行为正确 |
| save_closure 后 queue/handoff 还在 | 测试确认 store 行为正确 |
