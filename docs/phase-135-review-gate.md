# M135 Review Gate: Checkpoint Restore Semantics

## 范围

M135 为 checkpoint 增加真实、显式、安全的文件级恢复语义。恢复不是自动回滚，不执行 git reset，不绕过人工确认。

## 检查项

- [x] `CheckpointService.restore()` 已实现。
- [x] restore 未显式确认时不写入文件。
- [x] restore 只写 workspace 内的 checkpoint 文件。
- [x] `.env`、credentials、secret、私钥等秘密路径不进入 checkpoint 内容。
- [x] 秘密路径在 restore 时也不会写回。
- [x] `POST /checkpoints/{checkpoint_id}/restore` 已实现。
- [x] API 未确认时返回中文 400。
- [x] 未使用 `git reset` / `git checkout` 做回滚。
- [x] 未绕过 PermissionGate。
- [x] 未自动 approve。
- [x] 未 push / 未 release / 未 tag / 未 delete。

## Targeted Tests

- `uv run pytest services/agent-core/tests/test_checkpoint.py services/agent-core/tests/test_checkpoint_api.py -q`
  - 结果：17 passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1553 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 284 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `as any / unknown as`
  - 结果：无 M135 新增违规；命中均为既有规则文本、扫描器或测试样例
- renderer 暴露扫描
  - 结果：无 M135 新增 `ipcRenderer` / `node:fs` / `child_process` / `process.` 暴露
- 自动危险操作扫描
  - 结果：无 M135 新增自动 push/release/tag/delete/approve 入口

## 结论

M135 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M136。
