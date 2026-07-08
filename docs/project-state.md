# Bolt Project State

## 当前稳定基线

- 已完成到：M135 Checkpoint Restore Semantics（本地完成，待提交）。
- 最新远端基线：`origin/main = d52130d docs: mark M132 pushed`。
- 最新本地提交：`068c0bd feat(M134): feed tool results back into agent loop`。
- 当前本地分支：`main...origin/main [ahead 2]`。
- M133-M134 已本地提交，尚未 push。
- M135 已通过 targeted tests、full tests、quality 和 build，尚未提交。
- 未 release / 未 tag / 未 delete。
- 未进入 M136。

## M135 当前修复

- 新增真实 checkpoint restore 语义。
- restore 必须显式确认，未确认不写文件。
- restore 只写 workspace 内文件。
- checkpoint 创建时跳过秘密路径内容。
- restore 时秘密路径也会跳过。
- 新增 `POST /checkpoints/{checkpoint_id}/restore`，未确认返回中文 400。

## M135 关键文件

- `services/agent-core/src/bolt_core/checkpoint.py`
- `services/agent-core/src/bolt_core/app_routes.py`
- `services/agent-core/tests/test_checkpoint.py`
- `services/agent-core/tests/test_checkpoint_api.py`
- `docs/exec-plans/active/135-checkpoint-restore-semantics.md`
- `docs/decisions/135-checkpoint-restore-semantics.md`
- `docs/phase-135-review-gate.md`

## M135 验证

- Targeted tests：17 passed。
- Full backend tests：1553 passed。
- `pnpm run quality`：通过；shared 27 passed，desktop 39 files / 284 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M135 新增违规。
- renderer 暴露扫描：无 M135 新增暴露。
- 自动危险操作扫描：无 M135 新增自动 push/release/tag/delete/approve 入口。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- M135 文件有未提交改动。

## 下一步

- 提交 M135。
- 自动继续 M136：权限中心到真实执行链路的 UI/API 绑定收口。

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
