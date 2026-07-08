# M136 Review Gate: Permission Center Real Gate Binding

## 范围

M136 将权限中心从只读展示升级为真实 PermissionGate 入口。批准/拒绝仍复用既有后端路径，不新增自动批准能力。

## 检查项

- [x] `PermissionCenterItem` 返回 `request_id`。
- [x] 后端测试验证 permission-center 的 `request_id` 可用于真实批准。
- [x] 前端权限中心显示“批准并执行”和“拒绝”按钮。
- [x] 点击按钮后才调用 approve/reject。
- [x] 操作后刷新权限中心列表。
- [x] 失败时显示中文错误。
- [x] 未新增独立批准端点。
- [x] 未自动 approve。
- [x] 未绕过 PermissionGate。
- [x] 未 push / 未 release / 未 tag / 未 delete。

## Targeted Tests

- `pnpm --filter @bolt/desktop test -- PermissionCenterPanel harnessClientAutonomy`
  - 结果：39 files / 286 tests passed
- `uv run pytest services/agent-core/tests/test_permission_center.py services/agent-core/tests/test_permission_center_api.py -q`
  - 结果：14 passed

## Full Tests / Quality

- `uv run pytest -q`
  - 结果：1554 passed
- `pnpm run quality`
  - 结果：通过；shared 27 passed，desktop 39 files / 286 tests passed
- `pnpm --filter @bolt/desktop build`
  - 结果：通过
- `git diff --check`
  - 结果：通过（仅 Windows LF/CRLF 提示）
- `as any / unknown as`
  - 结果：无 M136 新增违规；命中均为既有规则文本、扫描器或测试样例
- renderer 暴露扫描
  - 结果：无 M136 新增 `ipcRenderer` / `node:fs` / `child_process` / `process.` 暴露
- 自动危险操作扫描
  - 结果：无 M136 新增自动 push/release/tag/delete/auto-approve 入口

## 结论

M136 review gate 通过。未 push / 未 release / 未 tag / 未 delete，未进入 M137。
