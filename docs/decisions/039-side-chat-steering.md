# M39 Decision: Side Chat Steering

## 决策
Side Chat 是用户 steering/上下文补充机制，不是权限绕过。

## 要点
- steering 消息通过 `/runs/{run_id}/steering` 进入 conversation
- pending_permission 不自动批准
- 不自动触发 agent loop
- 所有 UI 中文
- renderer 安全边界不变
