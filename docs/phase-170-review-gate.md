# M170 Review Gate: E2E Autonomous Loop

## 结论

复审修复中。M170 端到端自主循环已从硬编码 trace 改为调用 `OrchestratorEngine`，并补齐 Gate Freeze、认证 fetcher 与输入校验相关缺口。

## 原始验收

- `/orchestrator/autonomous-loop` 返回 status、verdict、rounds_completed、trace。
- `max_rounds` 被限制在 1-5。
- Gate 冻结时启动请求返回 423。
- Loop trace 包含 Planner、Researcher、Builder、Reviewer 等角色事件。

## 复审发现与修复

- P1：旧 `/permissions/{request_id}/approve` 可绕过 Gate Freeze。已修复为冻结时返回 423。
- P1：M165-M170 新面板直接使用 `window.fetch`，绕过桌面端认证 fetcher。已修复为统一接收父级 `fetcher`。
- P1：主题保存调用了未定义的 `saveDesktopSettings`。已修复为使用 `storeDesktopSettings` 和认证 fetcher。
- P2：非法 `max_rounds` 可能触发 500。已修复为返回 400。
- P2：M170 自主循环 trace 为合成结果。已修复为调用真实编排引擎。

## 待验证

- targeted backend tests
- targeted desktop panel tests
- desktop build
- `pnpm run quality`
- `uv run pytest -q`
- `git diff --check`
- Chinese UI 与 docs 检查

## 安全结论

- 未执行 push/release/tag/delete。
- 未自动批准权限。
- Gate Freeze 与 PermissionGate 必须同时生效。
- 自主循环只允许受限诊断闭环，不扩大为无门控写入执行。
