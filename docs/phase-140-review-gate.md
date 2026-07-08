# M140 Review Gate: Harness Execution Lock Boundary

## 结论

M140 通过。`submit_tool_request()` 的 auto-allowed 工具执行已移到 `_state_lock` 外，避免持锁执行真实工具。

## 检查项

- [x] 新增锁边界测试。
- [x] `_execute()` 被调用时当前线程不持有 `_state_lock`。
- [x] 保持 PermissionGate 决策不变。
- [x] 保持 pending permission 入队语义不变。
- [x] 保持 `file.write` / `file.patch` 人工批准语义不变。
- [x] 不自动 approve。
- [x] 不新增 push/release/tag/delete 入口。

## 验证

- Targeted harness tests：`19 passed`。
- Full backend tests：`1564 passed, 5 warnings`。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过；shared `27 passed`，desktop `39 files / 286 tests passed`。
- `pnpm lint:size`：通过。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- renderer 暴露扫描：无 M140 新增暴露。
- 自动危险操作扫描：无 M140 新增自动 push/release/tag/delete/auto-approve 入口。

## 下一步

外部复审中本批明确问题已收尾。等待爸爸复审后决定是否 push。
