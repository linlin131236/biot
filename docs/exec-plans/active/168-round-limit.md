# M168 Round Limit 执行计划

## 目标

把自主循环的最大失败/审查轮次固定为 5，避免睡觉模式无限消耗。

## 验收标准

- Orchestrator 最大 review rounds 为 5。
- Auto-continue 与 autonomous loop 对 max_rounds 做 1-5 上限约束。
- targeted tests 覆盖轮次上限。
- 不新增自动批准或危险命令入口。

## 风险

- 轮次上限必须在服务层执行，不能只靠前端输入限制。
