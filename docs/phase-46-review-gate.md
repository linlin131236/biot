# Phase 46 Review Gate

## 状态：已完成/已验证

## 后端
- 已验证：ExecutionHandoffService 创建 handoff 记录，不执行命令。
- 已验证：approved queue item 才能创建 handoff，未 approved 返回 409。
- 已验证：unknown queue item / handoff 返回 404。
- 已验证：同一个 queue item 不重复创建 handoff。
- 已验证：complete / fail 只改 handoff record，不改 queue item，不改 closure status。
- 已验证：completed / failed 是终态，不能互相改写，API 返回 409。

## API / Desktop
- 已验证：`GET /execution-handoffs` 按 closure_id 查询。
- 已验证：`POST /execution-queue/{item_id}/handoff` 只生成 handoff。
- 已验证：`POST /execution-handoffs/{id}/complete|fail` 只记录结果。
- 已验证：ExecutionHandoffPanel 中文显示安全交接。
- 已验证：manual_verification 只显示外部终端人工运行建议，不显示“执行命令”。
- 已验证：permission_panel 只引导去权限面板，不显示“批准权限”。
- 已验证：goal_input 只显示目标草稿文本，不调用 createGoal 或 runAgentLoop。
- 已验证：ExecutionQueuePanel 批准后只选择队列项用于交接，不自动生成 handoff。
- 已验证：切换闭环会清空已选 queue item，handoff 创建返回其他 closure_id 时不追加记录。

## 安全硬线
- queue approve 不是执行。
- handoff 不是执行。
- verification command 不自动运行。
- permission_panel 不批准权限。
- goal_input 不创建 goal，不启动 loop。
- M46 不做自动执行。
- M46 不进入 M47。
- 未 push。

## 安全扫描
- `rg "ipcRenderer|nodeIntegration|contextIsolation|\\bfs\\b|shell|process\\.env" apps/desktop/src`：有既有 CSS 类名、注释和测试字符串命中；M46 未新增 renderer 直接危险调用。
- `rg "as any|unknown as" apps/desktop/src packages/shared/src`：无输出。
- `rg "runAgentLoop|approvePermission|submit_tool_request|approve_permission|shell.execute|git push|release|delete" apps/desktop/src services/agent-core/src/bolt_core`：命中既有 Harness、GoalConsole、workflowClient 和测试路径；M46 handoff service/API/panel 未调用 runAgentLoop / approvePermission / submit_tool_request / approve_permission。

## 已跑验证
- `pytest tests/test_execution_handoff.py tests/test_execution_handoff_api.py tests/test_execution_queue.py tests/test_execution_queue_api.py -q`：39 passed。
- `pytest -q`：422 passed。
- `pnpm --filter @bolt/shared test`：25 passed。
- `pnpm --filter @bolt/desktop test -- ExecutionHandoffPanel`：通过。
- `pnpm --filter @bolt/desktop test`：187 passed。
- `pnpm --filter @bolt/desktop build`：通过，built in 507ms。
- `pnpm run quality`：通过；包含 shared 25 passed、desktop 187 passed，存在既有 React act(...) 警告但无失败。
- `node scripts/check-chinese-ui.mjs`：通过。
- `node scripts/check-docs.mjs`：通过。
- `git diff --check`：通过。
- `git status --short --ignored`：生成物仅显示为 ignored，未 staged。

## 自审
- 已检查：Handoff 不执行命令、不批准 PermissionGate、不创建 goal、不启动 loop。
- 已检查：queue item 未 approved 不能 handoff。
- 已检查：同一个 queue item 不重复创建 handoff。
- 已检查：新增 UI 为中文。
- 已检查：App 接线只传递 API 与状态，不自动生成 handoff，无 render loop。
- 已检查：无 `as any` / `unknown as`。
- 已检查：未 push。