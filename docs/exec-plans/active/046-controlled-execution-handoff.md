# M46 Controlled Execution Handoff

## 目标
把 M45 的安全执行队列推进到批准后的安全交接。handoff 只记录下一步人工处理意图，不执行命令、不批准权限、不创建目标、不启动 Agent Loop。

## 范围
- 新增 ExecutionHandoffRecord 与 ExecutionHandoffService。
- 新增 execution handoff API。
- shared protocol 与 desktop client 支持 handoff 类型和端点。
- 新增中文安全交接面板。
- 把已批准 queue item 交给 handoff 面板，由用户点击生成交接。

## 不做
- 不自动执行 verification command。
- 不自动批准 PermissionGate。
- 不自动创建 goal。
- 不自动 run agent loop。
- 不自动 push / release / delete。
- 不进入 M47。

## 交接语义
`queue approve` 不是执行，也不是 PermissionGate approve。`handoff` 也不是执行，只把 approved queue item 转为人工可处理记录。

## 类型映射
- `verification_command` -> `manual_verification`，显示命令，提示在外部终端人工运行。
- `waiting_permission` 相关 `manual_review` -> `permission_panel`，提示去权限面板处理原始请求。
- `repair_suggestion` -> `goal_input`，只生成目标草稿文本。
- `replan` -> `goal_input`，只生成重新规划目标草稿文本。
- 只读 `manual_review` -> `manual_review`。

## 验证
验证结果记录在 `docs/phase-46-review-gate.md`。M46 不做自动执行。