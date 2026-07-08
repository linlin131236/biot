# M137 Review Gate: Atomic Write Apply

## 范围

M137 修复批准补丁应用和 patch engine 的裸 `write_text()` 风险，改为同目录临时文件 + `os.replace()`。

## 检查项

- [x] 新增 `atomic_write_text()`。
- [x] `patch_engine.apply_change_set()` 使用原子写。
- [x] `ApprovalApplyEngine.apply()` create/modify 使用原子写。
- [x] modify 目标文件不存在时仍失败，不被原子写隐式创建。
- [x] 模拟 `os.replace` 失败时原文件保持不变。
- [x] 未新增自动 apply。
- [x] 未绕过 PermissionGate。
- [x] 未新增 push/release/tag/delete。

## Targeted Tests

- `uv run pytest services/agent-core/tests/test_patch_engine.py services/agent-core/tests/test_approval_apply.py -q`
  - 结果：25 passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1556 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 286 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `as any / unknown as`
  - 结果：无 M137 新增违规；命中均为既有规则文本、扫描器或测试样例
- 自动危险操作扫描
  - 结果：无 M137 新增自动 push/release/tag/delete/auto-approve 入口

## 结论

M137 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M138。
