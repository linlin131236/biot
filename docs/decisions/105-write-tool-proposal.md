# M105 Decision — Write Tool Proposal 写入工具提案

## 决策
WriteProposalStore + frozen WriteProposal dataclass，不落地 patch 到真实文件。

## 关键设计
- **不可变提案**：frozen dataclass，状态变更通过替换实例实现
- **Git HEAD 绑定**：每个 proposal 记录创建时的 git HEAD，防止过期 apply
- **路径安全验证**：继承 PathGuard，额外阻断 .claude/、锁文件等
- **删除操作强制高风险**：operation_type=delete 必须 risk_level=high/critical
- **提案生命周期**：pending → approved → applied / cancelled / stale

## 测试覆盖
- 21 tests：创建 (8)，查询 (4)，取消 (2)，过期检查 (2)，中文字段 (2)，边界条件 (2)
