# M50 Execution Dogfood Release Hardening

## 目标
用端到端 dogfood 验证 M48-M49 链路：任务闭环缺少验证证据 -> execution queue -> approve queue -> handoff -> request PermissionGate -> 用户批准权限 -> 执行结果 ingestion -> evidence -> assessment completed。

## 范围
- 新增后端 e2e dogfood 测试。
- 验证 request-permission 只生成 pending permission。
- 验证 approve permission 后才执行既有 Harness.approve_permission 路径。
- 验证 execution result 回写 handoff、queue、closure command evidence。
- 验证 assessment 根据 evidence 完成 closure。
- 做 release hardening 检查：size、quality、docs、Chinese UI、安全 rg、git status。

## 不做
- 不 release。
- 不 tag。
- 不 push。
- 不引入新执行能力。
- 不扩大到 arbitrary command automation。
- 不重构 Harness / PermissionGate / AgentLoop。

## 验证
- uv run pytest tests/test_execution_dogfood_e2e.py tests/test_execution_result_ingestion.py tests/test_execution_permission_bridge.py -q
- uv run pytest -q
- pnpm --filter @bolt/shared test
- pnpm --filter @bolt/desktop test
- pnpm --filter @bolt/desktop build
- pnpm run quality
- node scripts/check-chinese-ui.mjs
- node scripts/check-docs.mjs
- git diff --check
- git status --short --branch --ignored
- 安全扫描 rg 命令见 phase-50 review gate。
