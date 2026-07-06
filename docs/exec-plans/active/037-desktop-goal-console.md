# M37 Desktop Goal Console / 长任务驾驶舱

## Goal

让桌面端用户可以创建、启动、暂停、恢复、停止长任务，观察进度。

## Scope

- 新增 GoalConsole.tsx 组件（从 App.tsx 拆出）
- 补 harnessClientAutonomy 缺失方法（clearGoal、fetchGoalEvidence、fetchGoalBudget）
- App.tsx 接入 GoalConsole
- 全部 UI 中文

## Out of Scope

- 不新增危险工具
- 不自动审批权限
- 不默认后台无限运行
- max_steps 到达后必须停
- pending_permission 必须暂停
- 不进入 M38
- 不做 release/package

## Files Changed

- `apps/desktop/src/GoalConsole.tsx` — 长任务驾驶舱组件
- `apps/desktop/src/GoalConsole.test.tsx` — 红测试
- `apps/desktop/src/harnessClientAutonomy.ts` — 补 clearGoal/evidence/budget
- `apps/desktop/src/App.tsx` — 接入 GoalConsole
- `apps/desktop/src/uiWorkflowDogfood.test.tsx` — M37 测试
