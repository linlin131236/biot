# M143 Review Gate: Task Home Cockpit

## 结论

通过。M143 Task Home Cockpit 完成，首页已升级为带状态感知和安全推荐任务入口的 Agent 驾驶舱，且 targeted tests、desktop build、quality、后端全量和浏览器实机检查均通过。

## 变更摘要

- 首页新增“任务驾驶舱”区域。
- 驾驶舱显示当前项目、权限边界、运行状态、核心服务。
- 首页新增 6 个推荐任务卡片：
  - 读取文件并解释代码
  - 生成补丁预览
  - 运行白名单测试
  - 同步项目记忆
  - 整理项目文档
  - 查看执行时间线
- 新增 `LiquidGlassHomeInteraction.test.tsx`。
- 新增 `liquidGlassHomeInteraction.css`。
- 保留工程状态兼容层，避免旧测试和辅助技术语义断裂。

## 安全检查

- 未新增自动执行入口。
- 未新增自动批准入口。
- 未新增 push、release、tag、delete 入口。
- 未修改 PermissionGate。
- renderer 未暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 产品源码私人称呼扫描：无命中。

## 验证记录

- RED：`pnpm --filter @bolt/desktop test -- LiquidGlassHomeInteraction.test.tsx` 失败，原因是首页尚无“任务驾驶舱”和“推荐任务”区域。
- GREEN：`pnpm --filter @bolt/desktop exec vitest run src/LiquidGlassHomeInteraction.test.tsx --reporter verbose`：4 passed。
- 相关桌面测试：`LiquidGlassHomeInteraction`、`LiquidGlassWorkbench`、`LiquidGlassPrimitives`、`App`、`uiWorkflowDogfood`、`taskClosureDogfood`、`taskClosureAssessmentDogfood`：46 passed。
- `pnpm --filter @bolt/desktop test`：42 files / 294 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm run quality`：通过，shared 27 passed，desktop 42 files / 294 tests passed。
- `uv run pytest -q`：1564 passed，5 warnings。
- 浏览器实机检查：驾驶舱可见、6 个推荐任务卡可见、`biotBorderFlow=13s`、无乱码、无私人称呼。

## 已知风险

- M143 只增强首页入口体验，历史工程面板仍位于 legacy details 内，后续可逐步迁移到同一液态玻璃组件体系。
