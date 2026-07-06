# M48 PermissionGate-Bound Execution Bridge

## 目标
把 M46 handoff 往真实执行边界推进一步：approved handoff 可以生成一个 PermissionGate pending permission，但不执行命令、不自动批准。

## 范围
- 新增 ExecutionPermissionBridgeService。
- manual_verification handoff 可转换为 shell.execute pending permission。
- command 来自 handoff.command。
- workdir 固定为 app/harness workspace，不接受 UI 传入。
- handoff 记录保存 permission_request_id、permission_status、bridge_error。
- Desktop 只显示“申请人工执行权限”按钮并调用 request-permission API。

## 不做
- 不调用 Harness.submit_tool_request。
- 不调用 approve_permission。
- 不执行 shell。
- 不创建 goal。
- 不启动 Agent Loop。
- 不支持 permission_panel、goal_input、manual_review 进入 bridge。
- 不 push / release / tag / delete。

## API
- POST /execution-handoffs/{handoff_id}/request-permission

行为：
- handoff 不存在返回 404。
- 非 manual_verification 返回 409。
- 空 command 返回 409。
- terminal handoff 返回 409。
- 已有 permission_request_id 时返回原记录，不重复创建 permission。
- PermissionGate denied 时 handoff failed，记录 bridge_error，不创建 pending permission。
- PermissionGate 非 denied 时创建 pending permission，handoff status=waiting_permission，permission_status=pending_permission。

## 验证
- uv run pytest tests/test_execution_permission_bridge.py tests/test_execution_handoff.py tests/test_execution_handoff_api.py tests/test_execution_queue.py tests/test_execution_queue_api.py -q
- uv run pytest -q
- pnpm --filter @bolt/shared test
- pnpm --filter @bolt/desktop test -- ExecutionHandoffPanel
- pnpm --filter @bolt/desktop test
- pnpm --filter @bolt/desktop build
- pnpm run quality
- node scripts/check-chinese-ui.mjs
- node scripts/check-docs.mjs
- git diff --check
- 安全扫描 rg 命令见 phase-48 review gate。
