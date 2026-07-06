# M49 Execution Result Evidence Ingestion

## 目标
当用户在 PermissionGate 面板人工批准或拒绝 M48 生成的 permission request 后，把已有 approve_permission / reject_permission 返回的 ToolResult 回写到 handoff、queue 和 task closure evidence。

## 范围
- 新增 ExecutionResultIngestionService。
- approve_permission endpoint 保持既有权限语义，返回 ToolResult 后调用 ingestion。
- reject_permission endpoint 返回 rejected 后调用 ingestion。
- 只处理已登记在 handoff.permission_request_id 上的 ToolResult。
- unknown request_id 不影响任何 handoff。
- executed 后 handoff completed、queue item completed，并记录 verification command evidence。
- failed / rejected / denied 后 handoff failed、queue item failed，不记录 command evidence。
- terminal handoff 重复 ingestion 保持幂等，不改写结果。

## 不做
- 不新增自动 approve。
- 不新增自动 shell 调用。
- 不创建 goal。
- 不启动 Agent Loop。
- 不自动完成 closure；是否 completed 仍由既有 assessment API 判断。
- 不 push / release / tag / delete。

## 验证
- uv run pytest tests/test_execution_result_ingestion.py tests/test_execution_permission_bridge.py tests/test_execution_handoff_api.py tests/test_execution_queue_api.py tests/test_task_closure_assessment_api.py -q
- uv run pytest -q
- pnpm --filter @bolt/shared test
- pnpm --filter @bolt/desktop test
- pnpm --filter @bolt/desktop build
- pnpm run quality
- node scripts/check-chinese-ui.mjs
- node scripts/check-docs.mjs
- git diff --check
- 安全扫描 rg 命令见 phase-49 review gate。
