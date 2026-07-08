# Bolt Project State

## 当前稳定基线

- 已完成到：M132 Local API Auth + Workspace Lock（已 push）。
- 最新远端基线：`origin/main = 2798191 fix(M132): add local api auth and workspace lock`。
- 最新本地提交：`2798191 fix(M132): add local api auth and workspace lock`。
- 当前本地分支：`main` 与 `origin/main` 已同步。
- 已 push / 未 release / 未 tag / 未 delete。
- 未进入 M133。

## M132 当前修复

- 外部审计中确认成立：
  - 本地 FastAPI 缺少 token 门禁。
  - 桌面选择工作区没有成为后端硬边界。
- 外部审计中当前不成立：
  - `needs_replan` 未处理：当前 `AgentLoop.run_loop()` 已继续下一轮。
  - `risk.py` 纯黑名单：当前已覆盖危险命令变体与 pipe-to-interpreter 拦截。

## M132 关键文件

- `services/agent-core/src/bolt_core/local_api_auth.py`
- `services/agent-core/src/bolt_core/app.py`
- `services/agent-core/src/bolt_core/harness.py`
- `apps/desktop/electron/agentCoreRuntime.ts`
- `apps/desktop/electron/main.ts`
- `apps/desktop/electron/preload.ts`
- `apps/desktop/src/agentCoreAuth.ts`
- `apps/desktop/src/App.tsx`

## M132 验证

- 后端 targeted tests：20 passed。
- 桌面 targeted tests：39 files / 284 tests passed。
- 后端 full tests：1539 passed。
- `pnpm run quality`：通过。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无新增违规，命中均为规则文本、测试样例或扫描器字符串。
- renderer 暴露扫描：无实际 `ipcRenderer` / `node:fs` / `child_process` / `process.` 引用，命中均为注释。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- 除 M132 工作文件外无其他已知改动。

## 下一步

- 等待爸爸决定下一步是否进入 M133。

## 长期硬规则

- 所有用户可见 UI 必须中文。
- 不自动 push、release、tag、delete。
- 不进入未授权 milestone。
- 不绕过 PermissionGate。
- 不自动执行危险命令。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
