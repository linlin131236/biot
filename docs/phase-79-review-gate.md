# Phase 79 Review Gate — Memory Search UI

## 状态：✅ 通过

## 范围
- 新增 `MemorySearchPanel.tsx`：中文只读记忆搜索面板
- Tabs：全部 / 决策 / 失败 / 偏好 / 项目 / 代码地图
- 支持关键词搜索、分类筛选
- 结果显示：类型标签、中文摘要、source_refs、严重度标签（失败记录）
- 不提供写入、删除、执行按钮
- 不显示 secret
- 不暴露 ipcRenderer/fs/shell/process
- 新增 shared 类型：`MemorySearchResult`, `MemorySearchCategory`
- 新增 API client 方法：`fetchMemoryDecisions`, `fetchMemoryFailures`, `fetchMemoryPreferences`, `fetchProjectProfile`, `fetchCodeMapEntries`
- 集成到 `PanelsSection.tsx`

## 测试
- shared tests：27 passed
- desktop tests：206 passed（195 → 206，+11 new tests）
- desktop build：通过

## 验收
- [x] 搜索关键词能查到 decision/failure/preference/code map
- [x] 空结果中文提示
- [x] 敏感记忆显示脱敏/阻断提示（后端权限边界处理）
- [x] 前端 tests 覆盖渲染、搜索、filter、无危险对象
- [x] `pnpm --filter @bolt/desktop test` 通过
- [x] `pnpm --filter @bolt/desktop build` 通过

## 安全边界
- [x] renderer 不暴露 ipcRenderer/fs/shell/process
- [x] 无写入/删除/执行按钮
- [x] 不展示 secret
- [x] 不绕过 PermissionGate

## 是否允许进入 M80
**✅ 是。M79 Memory Search UI 达标，允许进入 M80 Memory Dogfood。**
