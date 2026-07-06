# M37 Desktop Goal Console

## Status

Accepted.

## Context

后端已有完整 Goal API（create/pause/resume/clear/evidence/budget），前端已有 harnessClientAutonomy 的 createGoal/pauseGoal/resumeGoal/getGoal，但没有 UI 组件让用户操作。

## Decision

- 从 App.tsx 拆出 GoalConsole.tsx 组件
- GoalConsole 接收 workspace 状态，无 workspace 时禁用启动
- pending_permission 时显示"等待人工批准"，不自动继续
- max_steps 到达后显示"已达到最大步数"，必须停止
- 所有按钮/状态/提示中文
- API 调用通过 props 注入，不直接访问 fs/shell/process

## Consequences

- 用户可在桌面端完整控制长任务生命周期
- 不暴露任意 shell/fs/process 能力
- 不自动审批权限请求
