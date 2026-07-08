# Bolt Project State

## 当前稳定基线

- 已完成到：M136 Permission Center Real Gate Binding（本地已提交，待 push）。
- 最新远端基线：`origin/main = d52130d docs: mark M132 pushed`。
- 最新本地提交：`HEAD feat(M136): bind permission center to real gate decisions`。
- 当前本地分支：`main...origin/main [ahead 4]`。
- M133-M136 已本地提交，尚未 push。
- M136 已通过 targeted tests、full tests、quality 和 build。
- 未 release / 未 tag / 未 delete。
- 未进入 M137。

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

## M136 当前修复

- 权限中心返回真实 `request_id`。
- 桌面权限中心新增“批准并执行”和“拒绝”按钮。
- 按钮复用既有 `/permissions/{request_id}/approve` 与 `/reject`。
- 操作必须由爸爸点击触发，不自动 approve。
- 操作后刷新权限中心列表并显示中文结果。

## M136 关键文件

- `services/agent-core/src/bolt_core/permission_center.py`
- `services/agent-core/tests/test_permission_center_api.py`
- `apps/desktop/src/PermissionCenterPanel.tsx`
- `apps/desktop/src/PermissionCenterPanel.test.tsx`
- `apps/desktop/src/harnessClientAutonomy.ts`
- `apps/desktop/src/harnessClientAutonomy.test.ts`
- `apps/desktop/src/PanelsSection.tsx`
- `docs/exec-plans/active/136-permission-center-real-gate-binding.md`
- `docs/decisions/136-permission-center-real-gate-binding.md`
- `docs/phase-136-review-gate.md`

## M136 验证

- Targeted desktop tests：39 files / 286 tests passed。
- Targeted backend tests：15 passed（含 M100 dogfood 回归）。
- Full backend tests：1554 passed。
- `pnpm run quality`：通过；shared 27 passed，desktop 39 files / 286 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M136 新增违规。
- renderer 暴露扫描：无 M136 新增暴露。
- 自动危险操作扫描：无 M136 新增自动 push/release/tag/delete/auto-approve 入口。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- 已跟踪文件干净；`.claude/` 未跟踪、未提交，按规则保持。

## 下一步

- 暂停在 M136，等待爸爸确认是否继续 M137。

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
