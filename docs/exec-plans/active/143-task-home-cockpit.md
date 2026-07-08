# M143 Task Home Cockpit

## 目标

把首页从“高级输入框”升级成 Agent 任务驾驶舱：用户进入桌面端后可以立刻看见当前项目、权限边界、运行状态、核心服务状态，并从安全推荐任务开始工作。

## 范围

- 新增首页任务驾驶舱。
- 新增 6 个推荐任务卡片。
- 推荐任务只复用已有 UI 回调，不新增执行能力。
- 新增 `LiquidGlassHomeInteraction.test.tsx`。
- 新增 `liquidGlassHomeInteraction.css`。
- 保持旧测试依赖的工程状态结构可访问。

## 非目标

- 不改 Agent Core 执行逻辑。
- 不新增自动批准、自动执行、push、release、tag、delete。
- 不修改 PermissionGate。
- 不重写设置页或历史面板。

## 验收标准

- 首页显示“任务驾驶舱”。
- 首页显示当前项目、权限边界、运行状态、核心服务。
- 推荐任务卡片包含读取文件、待批准权限、白名单测试、项目记忆、项目文档、执行时间线。
- 未选择工作区时，工作区相关推荐任务不可点击。
- 未创建运行时，依赖运行轨迹的任务不可点击。
- 产品源码不出现私人称呼。
- targeted tests、desktop build、quality、backend pytest、浏览器检查全部通过。
