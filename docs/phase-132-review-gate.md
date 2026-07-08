# M132 Review Gate: Local API Auth + Workspace Lock

## 范围

M132 修复外部审计中确认成立的本地安全问题：
- 本地 FastAPI 缺少调用门禁。
- 桌面选择工作区没有成为后端硬边界。

## 检查项

- [x] `/health` 保持公开。
- [x] 受保护 API 在配置 token 后无 token 返回 401。
- [x] 正确 bearer token 可访问受保护 API。
- [x] Electron runtime 生成/继承 token，并通过环境变量传递。
- [x] token 不进入命令行 args。
- [x] preload 只暴露 `selectWorkspace` 和 `agentCoreAuth`，不暴露通用 IPC。
- [x] renderer 默认 fetcher 自动附加 bearer token。
- [x] locked workspace 拒绝锁外 run workspace。
- [x] locked workspace 允许锁内子目录。
- [x] 未显式 project_dir/BOLT_WORKSPACE 的 `create_app()` 保持历史兼容。
- [x] 未 push / 未 release / 未 tag / 未 delete。
- [x] 未进入 M133。

## Targeted Tests

- `uv run pytest services/agent-core/tests/test_harness_workspace.py services/agent-core/tests/test_execution_dogfood_e2e.py services/agent-core/tests/test_task_closure_integration.py services/agent-core/tests/test_permission_request_recovery.py services/agent-core/tests/test_local_api_auth.py services/agent-core/tests/test_harness_workspace_lock.py -q`
  - 结果：20 passed
- `pnpm --filter @bolt/desktop test -- App coreClient harnessClient agentCoreRuntime agentCoreAuth preloadBridge`
  - 结果：39 files / 284 tests passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1539 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 284 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `rg -n "as any|unknown as" apps packages services --glob "!**/*.md"`
  - 结果：无新增违规；命中均为规则文本、测试样例或扫描器字符串
- renderer 暴露扫描：
  - 结果：无实际 `ipcRenderer` / `node:fs` / `child_process` / `process.` 引用，命中均为注释

## 结论

M132 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M133。
