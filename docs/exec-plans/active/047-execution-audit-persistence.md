# M47 Execution Audit Persistence

## 目标
把 M45/M46 的 execution queue 和 execution handoff 从内存态升级为可恢复审计记录。App 重启后，队列项、批准状态、交接记录、完成/失败结果必须能恢复。

## 范围
- 新增 ExecutionAuditStore，使用 JSON 保存 queue items 与 handoff records。
- ExecutionQueueService 初始化时恢复 queue items，并在 create / approve / reject / complete / fail 后保存。
- ExecutionHandoffService 初始化时恢复 handoff records，并在 create / complete / fail 后保存。
- App 创建同一个 store，让 queue service 和 handoff service 共享审计状态。
- API 测试通过临时路径验证 app/service 重建后的恢复能力。

## 不做
- 不执行 verification command。
- 不批准 PermissionGate。
- 不创建 goal。
- 不启动 Agent Loop。
- 不调用 shell.execute / Harness.submit_tool_request / approve_permission / runAgentLoop。
- 不 push / release / tag / delete。
- 不进入 M48。

## 文件清单
- services/agent-core/src/bolt_core/execution_audit_store.py
- services/agent-core/src/bolt_core/execution_queue.py
- services/agent-core/src/bolt_core/execution_handoff.py
- services/agent-core/src/bolt_core/app.py
- services/agent-core/tests/test_execution_audit_store.py
- services/agent-core/tests/test_execution_queue.py
- services/agent-core/tests/test_execution_handoff.py
- services/agent-core/tests/test_execution_queue_api.py
- services/agent-core/tests/test_execution_handoff_api.py
- docs/decisions/047-execution-audit-persistence.md
- docs/phase-47-review-gate.md
- docs/project-state.md

## 状态机保持不变
- queue pending duplicate 仍只对 pending duplicate 去重。
- queue approve / reject 仍只允许 pending。
- workspace_write pending item 仍不能直接 complete。
- queue failed 仍要求 approved。
- handoff 仍要求 queue item approved。
- 同一个 queue item 仍不能重复创建 handoff。
- handoff completed / failed 仍是终态，不能互相改写。
- handoff complete / fail 不改 queue item 状态，不改 closure 状态。

## 持久化 schema
```json
{
  "version": 1,
  "queue_items": [],
  "handoff_records": []
}
```

持久化规则：
- 使用 UTF-8 JSON。
- 写入先写 tmp 文件，再 os.replace 原子替换。
- 父目录不存在时创建。
- 文件不存在时返回空状态。
- JSON 损坏时抛出明确异常，不静默覆盖。
- 默认路径为工作区 `.bolt/execution-audit.json`。
- 可通过 `BOLT_EXECUTION_AUDIT_PATH` 或 `create_app(path)` 注入路径。

## 验证命令
- `uv run pytest tests/test_execution_audit_store.py tests/test_execution_queue.py tests/test_execution_handoff.py tests/test_execution_queue_api.py tests/test_execution_handoff_api.py -q`
- `uv run pytest -q`
- `pnpm --filter @bolt/shared test`
- `pnpm --filter @bolt/desktop test`
- `pnpm --filter @bolt/desktop build`
- `pnpm run quality`
- `node scripts/check-chinese-ui.mjs`
- `node scripts/check-docs.mjs`
- `git diff --check`
- 安全扫描 rg 命令见 phase-47 review gate。

## 安全硬线
- persistence 只是审计恢复，不是执行授权。
- queue approve 仍不等于执行。
- handoff 仍不等于执行。
- 不自动运行 verification command。
- 不自动批准 PermissionGate。
- 不调用 Harness、PermissionGate、Agent Loop 或 shell 执行路径。
- renderer 不新增 ipcRenderer / fs / shell / process。
- 不使用 `as any` / `unknown as`。
