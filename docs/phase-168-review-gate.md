# M168 Review Gate: Round Limit

## 结论

PASS。自动继续与自主循环轮次被限制在 1-5。

## 验证

- `AutoContinueService.set_auto_continue(True, 99)` 返回 `max_rounds=5`。
- `AutonomousLoopService.run_loop(..., 50)` 返回 `max_rounds=5`。
- Orchestrator review rounds 已调整为 5。

## 安全

- 有硬停止条件。
- 未新增无限循环入口。
