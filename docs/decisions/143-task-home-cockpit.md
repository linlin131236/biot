# Decision 143: Task Home Cockpit

## 决策

在 Liquid Glass 首页增加任务驾驶舱与推荐任务卡片，把状态感知和安全入口放在首屏核心区域。

## 原因

M141-M142 已经确定液态玻璃视觉方向和组件 primitives，但首页仍偏“漂亮输入框”。Agent 桌面产品需要在首屏表达三件事：

- 当前是否有可工作的项目上下文。
- 写入是否仍受人工批准保护。
- 可以从哪些安全任务开始。

因此 M143 先补首页交互密度，而不是继续扩展后端能力。

## 方案

- `LiquidGlassHome` 内部派生 cockpit 状态，不改后端数据模型。
- 推荐任务卡片复用已有回调：
  - `refreshTrace`
  - `refreshPermissions`
  - `runReview`
  - `refreshMemory`
  - `runGardener`
  - `fetchTimeline`
- 未选择工作区时禁用工作区相关卡片。
- 用独立 CSS 文件承载 M143 样式，避免 `liquidGlassHome.css` 超过 size gate。
- 保留隐藏兼容状态层，避免旧测试和辅助技术失去工程状态语义。

## 安全边界

- M143 只改 renderer UI。
- 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 不新增自动执行、自动批准或发布入口。
- 所有可见文案为中文。
- 软件产品内不使用私人称呼。
