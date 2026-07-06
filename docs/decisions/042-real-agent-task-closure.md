# M42 Decision: Real Agent Task Closure

## 决策
M42 是任务闭环强化，不是能力扩张或发布。

## 要点
- TaskClosureService 只记录证据，不执行工具
- 不自动 push / release / delete
- 不自动审批 permission
- 不写 workspace 外
- 失败修复最多 3 次重试
- 审查面板只读展示
- 所有 UI 中文
- fetcher 注入一致
