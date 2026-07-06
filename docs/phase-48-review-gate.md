# Phase 48 Review Gate

## 状态：已完成/已验证

## 后端
- 已实现：ExecutionPermissionBridgeService 使用 request-only 路径创建 pending permission。
- 已实现：manual_verification handoff 转 shell.execute ToolRequest。
- 已实现：workdir 固定来自 harness workspace。
- 已实现：PermissionGate denied 时 handoff failed，记录 bridge_error，不排队。
- 已实现：重复 request-permission 不重复创建 permission。
- 已实现：非 manual_verification、空 command、terminal handoff 返回 409。
- 已实现：handoff 持久化 permission_request_id、permission_status、bridge_error，并兼容旧审计 JSON。

## API / Desktop
- 已实现：POST /execution-handoffs/{handoff_id}/request-permission。
- 已实现：Desktop 显示中文按钮“申请人工执行权限”。
- 已实现：Desktop 点击后只调用 request-permission API。
- 已实现：Desktop 显示“等待人工执行权限”和“申请失败：...”中文状态。

## 安全硬线
- 未调用 Harness.submit_tool_request。
- 未调用 approve_permission。
- 未调用 shell executor。
- 未创建 goal。
- 未启动 Agent Loop。
- 未自动批准 PermissionGate。
- 未绕过 PermissionGate。
- 未 push / release / tag / delete。
- renderer 未新增 ipcRenderer / fs / shell / process。
- 未使用 `as any` / `unknown as`。

## 已跑验证
- `uv run pytest tests/test_execution_permission_bridge.py tests/test_execution_handoff.py tests/test_execution_handoff_api.py tests/test_execution_queue.py tests/test_execution_queue_api.py -q`：64 passed。
- `uv run pytest tests/test_app.py::test_agent_step_endpoint_records_llm_trace tests/test_harness.py::test_internal_run_registration_does_not_capture_perception_memory tests/test_execution_permission_bridge.py tests/test_execution_handoff.py tests/test_execution_handoff_api.py -q`：35 passed；随后测试合并到既有 perception 测试以满足 size gate。
- `uv run pytest -q`：456 passed。
- `pnpm --filter @bolt/shared test`：25 passed。
- `pnpm --filter @bolt/desktop test -- ExecutionHandoffPanel`：ExecutionHandoffPanel 11 tests passed；命令实际跑到 desktop 套件，全部通过。
- `pnpm --filter @bolt/desktop test -- ExecutionHandoffPanel harnessClientAutonomy PanelsSection App`：受影响 desktop 测试全部通过。
- `pnpm --filter @bolt/desktop test`：通过。
- `pnpm --filter @bolt/desktop build`：通过，Vite built in 293ms。
- `pnpm run quality`：通过；仍有既有 React act(...) 警告但无失败。
- `node scripts/check-chinese-ui.mjs`：通过。
- `node scripts/check-docs.mjs`：通过。
- `git diff --check`：通过，仅 LF/CRLF 工作区提示。
- `rg "as any|unknown as" apps/desktop/src packages/shared/src`：无输出。
- `rg "ipcRenderer|nodeIntegration|contextIsolation|\\bfs\\b|shell|process\\.env" apps/desktop/src`：仅既有样式类名、注释、测试字符串、harness client 测试和 M48 安全断言命中；未新增 renderer 危险能力。
- `rg "submit_tool_request|approve_permission|runAgentLoop|shell.execute|git push|release|delete" services/agent-core/src/bolt_core apps/desktop/src`：命中既有 Harness/API/tool schema/GoalConsole/tests、安全文案，以及 M48 bridge 构造 shell.execute ToolRequest；request-permission 未调用 submit_tool_request、approve_permission、runAgentLoop 或 shell executor。

## Reviewer 审核
- 未发现 blocker / critical。
- 已确认 request-permission 不自动执行命令。
- 已确认未绕过 PermissionGate。
- 已确认 queue approve 没有被当成真实权限批准。
- 已确认 handoff 没有被当成真实执行。
- 已确认 App/PanelsSection 已真实接入 requestExecutionHandoffPermission。
- 残余风险：permission 批准/拒绝后的 handoff 状态同步属于 M49 范围；前端“不调用 Node/Electron 能力”单测表达力有限，静态扫描作为主要保障。

## 自审
- 已检查：diff 只包含 M48 bridge、API、protocol、Desktop、tests、docs。
- 已检查：queue approve 仍不是执行权限批准。
- 已检查：handoff 仍不是执行。
- 已检查：request-permission 只创建 pending permission。
- 已检查：PermissionGate denied 不进入 permission queue。
- 已检查：app.py 当前 299 行。

## 是否 push
- 未 push。
