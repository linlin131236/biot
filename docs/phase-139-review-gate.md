# M139 Review Gate: Tool Operation Registry

## 结论

M139 通过。工具操作映射已归一到共享模块，`file.patch` 不再被 FakeModelGateway 误标为 `read`。

## 检查项

- [x] 新增 `tool_operations.py` 单一映射入口。
- [x] `agent_loop.py` 使用共享映射。
- [x] `model_gateway.py` 使用共享映射。
- [x] 删除重复私有映射。
- [x] `file.patch` 映射为 `patch`。
- [x] terminal 工具映射完整。
- [x] web extract 映射完整。
- [x] 未知工具默认 `read`，不提升权限。
- [x] 不改变 PermissionGate。
- [x] 不新增自动执行、自动 approve、自动 push/release/tag/delete。

## 验证

- Targeted tests：`14 passed`。
- Full backend tests：`1563 passed, 5 warnings`。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过；shared `27 passed`，desktop `39 files / 286 tests passed`。
- `git diff --check`：通过（仅 Windows LF/CRLF 提示）。
- `as any / unknown as`：无 M139 新增违规。
- renderer 暴露扫描：无 M139 新增暴露。
- 自动危险操作扫描：无 M139 新增自动 push/release/tag/delete/auto-approve 入口。

## 下一步

继续 M140：缩小 `Harness.submit_tool_request()` 的锁范围，避免持锁执行工具。
