# M131 Exec Plan - Liquid Glass Desktop Shell

## 目标

把桌面端从工程面板观感升级为 Biot 自己的中文液态玻璃 Agent 工作台，覆盖深色/浅色主题、首页任务输入、设置中心骨架，同时保留现有任务、权限、补丁、测试和工程面板能力。

## 范围

- 新增液态玻璃桌面壳层组件。
- 新增中文首页：任务输入、项目、权限、安全状态、快捷动作。
- 新增中文设置中心骨架：常规、代码预览、模型设置、技能、子智能体、MCP 服务器、插件管理、命令、索引库、使用统计、引导。
- 保留既有 App 行为和测试路径，不新增自动执行、自动批准、push、release、tag、delete 入口。
- 拆分组件和 CSS，确保 size gate 通过。

## 验收

- 桌面 UI 可显示 Biot 液态玻璃首页。
- 支持深色/浅色主题切换。
- 设置中心中文分类完整。
- 旧工作流按钮和工程面板仍可访问。
- `pnpm --filter @bolt/desktop test` 通过。
- `pnpm --filter @bolt/desktop build` 通过。
- `pnpm run quality` 通过。
- `git diff --check` 通过。
