# M133 Review Gate: Real Model Gateway

## 范围

M133 修复生产默认模型网关问题，让 fake 只作为显式测试/开发 provider。

## 检查项

- [x] 默认模型设置不是 fake。
- [x] 默认 AgentLoop 使用真实网关路径。
- [x] 缺少 API key 时明确失败。
- [x] 缺少 API key 时不会启动工具执行。
- [x] 显式 `provider=fake` 仍可用于测试。
- [x] App 层 agent step 缺 key fail closed。
- [x] API key 不出现在 model settings status 返回中。
- [x] 未 push / 未 release / 未 tag / 未 delete。
- [x] 未进入 M134 前已完成 M133 targeted tests。

## Targeted Tests

- `uv run pytest services/agent-core/tests/test_model_gateway.py services/agent-core/tests/test_model_settings.py services/agent-core/tests/test_agent_loop.py services/agent-core/tests/test_app.py services/agent-core/tests/test_app_model_gateway.py -q`
  - 结果：39 passed
- `pnpm --filter @bolt/desktop test -- App uiWorkflowDogfood`
  - 结果：39 files / 284 tests passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1545 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 284 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `pnpm lint:size`
  - 结果：通过；模型 app 测试已拆出 `test_app_model_gateway.py`，未新增豁免
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `as any / unknown as`
  - 结果：无新增违规；命中均为规则文本、测试样例或扫描器字符串
- renderer 暴露扫描
  - 结果：无实际 `ipcRenderer` / `node:fs` / `child_process` / `process.` 引用，命中均为注释
- 自动危险操作扫描
  - 结果：无新增自动 push/release/tag/delete/approve 入口，命中均为既有审批函数、评估测试或禁止文案

## 结论

M133 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M134。
