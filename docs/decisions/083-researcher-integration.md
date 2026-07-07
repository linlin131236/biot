# Decision 083 — Researcher Integration

## 决策
接入 Researcher 只读角色：创建研究摘要（ResearchBrief），产出结构化摘要（ResearchSummary），强制 source_refs，限 2-4 篇资料。

## 关键设计
- 5 种研究范围：project_docs / bincloud_refs / code_map / decision_memory / failure_memory
- 2-4 篇资料硬限制
- source_refs 为空硬阻断
- 跨范围引用仅警告
- 原则和风险提取

## 结果
- 28 tests 通过
- 所有端点只读
- 中文 UI
