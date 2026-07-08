# Bolt Project State

## 当前稳定基线

- 已完成到：M139 Tool Operation Registry（本地已提交，待 push）。
- 最新远端基线：`origin/main = d52130d docs: mark M132 pushed`。
- 最新本地提交：`HEAD fix(M139): centralize tool operation mapping`。
- 当前本地分支：`main...origin/main [ahead 7]`。
- M133-M139 已本地提交，尚未 push。
- M139 已通过 targeted tests、full backend、quality 和 build。
- 未 release / 未 tag / 未 delete。
- 未进入 M140。

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

## M137 当前修复

- 新增 `atomic_write_text()`。
- `patch_engine.apply_change_set()` 改用原子写。
- `approval_apply.py` 的 create/modify 写入改用原子写。
- modify 目标不存在时仍失败，不被隐式创建。

## M137 关键文件

- `services/agent-core/src/bolt_core/atomic_write.py`
- `services/agent-core/src/bolt_core/patch_engine.py`
- `services/agent-core/src/bolt_core/approval_apply.py`
- `services/agent-core/tests/test_patch_engine.py`
- `services/agent-core/tests/test_approval_apply.py`
- `docs/exec-plans/active/137-atomic-write-apply.md`
- `docs/decisions/137-atomic-write-apply.md`
- `docs/phase-137-review-gate.md`

## M137 验证

- Targeted tests：25 passed。
- Full backend tests：1556 passed。
- `pnpm run quality`：通过；shared 27 passed，desktop 39 files / 286 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M137 新增违规。
- 自动危险操作扫描：无 M137 新增自动 push/release/tag/delete/auto-approve 入口。

## M138 当前修复

- `AgentLoop.run_loop()` 维护 messages 历史。
- 模型 tool_calls 会追加 assistant tool_calls 消息。
- 工具结果以 `role="tool"` 消息回灌给下一轮。
- 同一轮多个 tool_calls 会顺序执行。
- 默认 loop 上限从 3 提升到 50。
- LLM 失败立即停止，不消耗 50 步。

## M138 关键文件

- `services/agent-core/src/bolt_core/agent_loop.py`
- `services/agent-core/src/bolt_core/model_gateway.py`
- `services/agent-core/src/bolt_core/harness.py`
- `services/agent-core/src/bolt_core/harness_api.py`
- `services/agent-core/tests/test_agent_loop.py`
- `docs/exec-plans/active/138-agent-loop-tool-message-history.md`
- `docs/decisions/138-agent-loop-tool-message-history.md`
- `docs/phase-138-review-gate.md`

## M138 验证

- Targeted agent loop/model tests：26 passed。
- Targeted closure/API regression：35 passed。
- Full backend tests：1560 passed。
- `pnpm run quality`：通过；shared 27 passed，desktop 39 files / 286 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M138 新增违规。
- renderer 暴露扫描：无 M138 新增暴露。
- 自动危险操作扫描：无 M138 新增自动 push/release/tag/delete/auto-approve 入口。

## M139 当前修复

- 新增 `tool_operations.py` 作为工具名到操作类型的共享入口。
- `AgentLoop` 提交 tool call 时使用共享映射。
- `FakeModelGateway` 生成测试内容时使用共享映射。
- 修复 `file.patch` 在 fake gateway 内容中被误标为 `read` 的问题。
- 删除 `agent_loop.py` 和 `model_gateway.py` 的重复私有映射。

## M139 关键文件

- `services/agent-core/src/bolt_core/tool_operations.py`
- `services/agent-core/src/bolt_core/agent_loop.py`
- `services/agent-core/src/bolt_core/model_gateway.py`
- `services/agent-core/tests/test_tool_operations.py`
- `services/agent-core/tests/test_model_gateway.py`
- `docs/exec-plans/active/139-tool-operation-registry.md`
- `docs/decisions/139-tool-operation-registry.md`
- `docs/phase-139-review-gate.md`

## M139 验证

- Targeted tests：14 passed。
- Full backend tests：1563 passed。
- `pnpm run quality`：通过；shared 27 passed，desktop 39 files / 286 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M139 新增违规。
- renderer 暴露扫描：无 M139 新增暴露。
- 自动危险操作扫描：无 M139 新增自动 push/release/tag/delete/auto-approve 入口。

## 工作区状态

- `.claude/` 未跟踪、未提交，按规则保持。
- 已跟踪文件干净；`.claude/` 未跟踪、未提交，按规则保持。

## 下一步

- 提交 M139 后继续 M140：缩小 `submit_tool_request` 锁范围。

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
