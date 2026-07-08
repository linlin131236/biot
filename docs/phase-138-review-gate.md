# M138 Review Gate: Agent Loop Tool Message History

## 范围

M138 将 Agent Loop 从摘要回填推进为 messages 历史维护：assistant tool_calls 与 tool role 结果消息会进入下一轮模型请求。

## 检查项

- [x] `ModelMessage` 支持 `tool_call_id`。
- [x] `ModelMessage` 支持 assistant `tool_calls`。
- [x] OpenAI-compatible gateway 序列化 tool messages。
- [x] `run_loop()` 维护 messages 历史。
- [x] 工具结果作为 `role="tool"` 消息进入下一轮。
- [x] 同一轮多个 tool_calls 能顺序执行。
- [x] pending/failed/denied 不继续执行后续工具。
- [x] 默认 loop 上限为 50。
- [x] LLM 失败立即停止。
- [x] 未绕过 PermissionGate。
- [x] 未自动 approve。
- [x] 未 push / 未 release / 未 tag / 未 delete。

## Targeted Tests

- `uv run pytest services/agent-core/tests/test_agent_loop.py services/agent-core/tests/test_model_gateway.py services/agent-core/tests/test_app_model_gateway.py -q`
  - 结果：26 passed
- `uv run pytest services/agent-core/tests/test_app.py services/agent-core/tests/test_task_closure_integration.py services/agent-core/tests/test_task_closure_assessment_integration.py services/agent-core/tests/test_integration_smoke.py services/agent-core/tests/test_dogfood_smoke.py -q`
  - 结果：35 passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1560 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 286 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `as any / unknown as`
  - 结果：无 M138 新增违规；命中均为既有规则文本、扫描器或测试样例
- renderer 暴露扫描
  - 结果：无 M138 新增 `ipcRenderer` / `node:fs` / `child_process` / `process.` 暴露
- 自动危险操作扫描
  - 结果：无 M138 新增自动 push/release/tag/delete/auto-approve 入口

## 结论

M138 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M139。
