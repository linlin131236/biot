# M41 Decision: End-to-End Dogfood Reliability

## 决策
M41 是可靠性闭环，不是能力扩展。

## 要点
- 不新增 Agent 能力
- 不自动恢复长任务
- 不自动审批 permission
- 不自动 rollback checkpoint
- Side Chat = steering only
- Checkpoint = audit/preview only
- 所有 UI 中文
- fetcher 注入一致
