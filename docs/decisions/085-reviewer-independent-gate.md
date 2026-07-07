# Decision 085 — Reviewer Independent Gate

## 决策
独立审查门：评估审查包，阻断自我批准，按发现分类 approved/changes_requested/blocked。

## 关键设计
- 自我批准硬阻断（builder_context == reviewer_context → blocked）
- 缺 evidence/source_refs → blocked
- P1 → blocked, P2 → changes_requested
- 缺测试 → changes_requested

## 结果
- 8 tests 通过
