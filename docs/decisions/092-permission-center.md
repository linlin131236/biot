# M92 Decision — 权限中心

## 决策
新增只读聚合端点 `GET /permission-center` 和对应桌面面板 `PermissionCenterPanel`，集中展示权限请求的中文风险解释。

## 选型
- **风险分类**：基于工具名+操作名自动分类（shell_executor/write→高风险，read→中风险，search→低风险）
- **中文解释**：每条权限附带风险说明、批准后影响、建议动作
- **只读边界**：不新增 approve/reject 端点，审批只能走 PermissionGate 路径
- **排序**：高风险优先展示

## 实现内容
- `permission_center.py` (179 行)：风险分类 + 中文解释 + 聚合服务
- `permission_center_api.py` (26 行)：单端点 GET /permission-center
- `PermissionCenterPanel.tsx` (170 行)：中文权限中心面板
- `PermissionCenterPanel.test.tsx` (110 行)：9 tests
- `test_permission_center.py` (123 行)：13 tests
- `harnessClientAutonomy.ts`：+fetchPermissionCenter
- `PanelsSection.tsx`：+PermissionCenterPanel
- `app.py`：+import + include_router

## 测试结果
- 后端单元：13/13 passed
- 前端面板：9/9 passed（含在 27 files, 231 tests）
- Desktop build：passed
- 无 as any/unknown as
- 无 renderer 暴露
