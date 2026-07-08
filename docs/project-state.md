# Bolt Project State

## 当前稳定基线

- 已完成到：M133 Real Model Gateway（本地完成，待提交）。
- 最新远端基线：`origin/main = 2798191 fix(M132): add local api auth and workspace lock`。
- 最新本地提交：`d52130d docs: mark M132 pushed`。
- 当前本地分支：`main` 与 `origin/main` 基线同步，存在 M133 未提交修复。
- M132 已 push / M133 未 push / 未 release / 未 tag / 未 delete。
- 未进入 M134。

## M133 当前修复

- 外部审计中确认成立：
  - 生产默认仍可能走 `FakeModelGateway`。
- 已修复：
  - 新增 `DefaultModelGateway`。
  - 默认模型设置改为 `openai-compatible`，缺 key 明确失败。
  - `provider=fake` 仅作为显式测试/开发选择。
  - App 层 agent step 缺 key fail closed，不启动工具执行。

## M133 关键文件

- `services/agent-core/src/bolt_core/model_gateway.py`
- `services/agent-core/src/bolt_core/model_settings.py`
- `services/agent-core/src/bolt_core/agent_loop.py`
- `services/agent-core/tests/test_model_gateway.py`
- `services/agent-core/tests/test_model_settings.py`
- `services/agent-core/tests/test_agent_loop.py`
- `services/agent-core/tests/test_app.py`

## M133 验证

- 后端 targeted tests：39 passed。
- 桌面 targeted tests：39 files / 284 tests passed。
- 后端 full tests：1545 passed。
- `pnpm run quality`：通过。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无新增违规，命中均为规则文本、测试样例或扫描器字符串。
- renderer 暴露扫描：无实际 `ipcRenderer` / `node:fs` / `child_process` / `process.` 引用，命中均为注释。
- 自动危险操作扫描：无新增自动 push/release/tag/delete/approve 入口。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- 除 M133 工作文件外无其他已知改动。

## 下一步

- 提交 M133。
- 自动继续 M134：真实 Agent Loop tool-result 消息闭环。

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
