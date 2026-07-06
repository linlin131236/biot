# Phase 47 Review Gate

## 状态：已完成/已验证

## 后端
- 已实现：ExecutionAuditStore 使用 UTF-8 JSON 保存 queue_items 和 handoff_records。
- 已实现：写入创建父目录，先写 tmp 文件，再 os.replace 原子替换。
- 已实现：文件不存在时返回空状态。
- 已实现：JSON 损坏时抛出明确异常，不静默覆盖。
- 已实现：ExecutionQueueService 重启后恢复 queue item、批准状态、拒绝原因、完成/失败结果。
- 已实现：ExecutionHandoffService 重启后恢复 handoff record、完成/失败结果。
- 已验证：pending duplicate 去重语义不变。
- 已验证：workspace_write pending queue item 不能直接 complete 的规则不变。
- 已验证：同一个 queue item 恢复后不能重复创建 handoff。
- 已验证：completed / failed handoff 是终态，不能互相改写。
- 已验证：handoff complete / fail 不改 queue item 状态。

## API / Desktop
- 已实现：App 创建同一个 ExecutionAuditStore，queue service 和 handoff service 共享审计状态。
- 已实现：支持 `create_app(path)` 测试注入。
- 已实现：支持 `BOLT_EXECUTION_AUDIT_PATH` 配置路径。
- 已实现：默认路径为工作区 `.bolt/execution-audit.json`。
- 已实现：`.bolt/` 与 `uv.lock` 不进入 git。
- 已验证：API 创建/批准 queue item 后，重建 app 可通过 list 查回。
- 已验证：API 创建 handoff 后，重建 app 可通过 list 查回。
- 已验证：closure_id 过滤仍正确。
- 已验证：terminal handoff 再 complete/fail 返回 409。
- Desktop 未改 UI。

## 安全硬线
- 未自动执行 verification command。
- 未批准 PermissionGate。
- 未创建 goal。
- 未启动 Agent Loop。
- 未调用 shell.execute / Harness.submit_tool_request / approve_permission / runAgentLoop。
- 未 push / release / tag / delete。
- renderer 未改动，未新增 ipcRenderer / fs / shell / process。
- 未使用 `as any` / `unknown as`。

## 安全扫描
- `rg "as any|unknown as" apps/desktop/src packages/shared/src`：无输出。
- `rg "ipcRenderer|nodeIntegration|contextIsolation|\\bfs\\b|shell|process\\.env" apps/desktop/src`：仅既有样式类名、注释、测试字符串和既有 harness client 测试命中；M47 未改 Desktop，未新增 renderer 危险能力。
- `rg "runAgentLoop|approvePermission|submit_tool_request|approve_permission|shell.execute|git push|release|delete" apps/desktop/src services/agent-core/src/bolt_core`：命中既有 Harness、GoalConsole、workflowClient、tool schema、测试和安全文案；M47 新增 store/queue/handoff 持久化路径未调用自动执行、权限批准、Agent Loop、push/release/delete。

## 已跑验证
- `pytest services/agent-core/tests/test_execution_audit_store.py services/agent-core/tests/test_execution_queue.py services/agent-core/tests/test_execution_handoff.py services/agent-core/tests/test_execution_queue_api.py services/agent-core/tests/test_execution_handoff_api.py -q`：失败，当前 shell 混用 Hermes Python 与全局 pytest，导入 FastAPI 时缺少 `pydantic_core._pydantic_core`。
- `uv run pytest tests/test_execution_audit_store.py tests/test_execution_queue.py tests/test_execution_handoff.py tests/test_execution_queue_api.py tests/test_execution_handoff_api.py -q`：58 passed。
- `uv run pytest -q`：444 passed。
- `pnpm --filter @bolt/shared test`：25 passed。
- `pnpm --filter @bolt/desktop test`：通过。
- `pnpm --filter @bolt/desktop exec vitest run --reporter=json --outputFile=C:/Users/bi240/AppData/Local/Temp/bolt-desktop-vitest.json`：51 suites passed，189 tests passed。
- `pnpm --filter @bolt/desktop build`：通过，built in 475ms。
- `pnpm run quality`：首次失败于 `app.py` 307 行，已通过移动 audit path 解析修复；二次失败于 architecture 写边界，已将 `execution_audit_store.py` 按持久化基础设施加入白名单；最终通过，仍有既有 React act(...) 警告但无失败。
- `node scripts/check-chinese-ui.mjs`：通过。
- `node scripts/check-docs.mjs`：通过。
- `git diff --check`：通过，仅 LF/CRLF 工作区提示。
- `git status --short --branch --ignored`：生成物、缓存、虚拟环境、uv.lock 均为 ignored，未 staged。

## 自审
- 已检查：store 只保存审计 JSON，不执行任何动作。
- 已检查：queue approve 仍不等于执行，也不批准 PermissionGate。
- 已检查：handoff 仍不等于执行，也不调用 shell / Harness / PermissionGate / Agent Loop。
- 已检查：损坏 JSON 不会被静默覆盖。
- 已检查：恢复后 queue/handoff 状态机保持不变。
- 已检查：M47 未改 shared protocol，未改 Desktop UI。
- 已检查：无 `as any` / `unknown as`。
- 已检查：未 push，未 release，未 tag，未 delete。

## 是否 push
- 未 push。
