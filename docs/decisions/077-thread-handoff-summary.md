# M77 Thread Handoff Summary — 设计决策

## 决策背景
M76 的 ContextCompaction 提供了通用压缩能力，但新窗口接手还需要 Git 状态、禁止事项、必读文档、下一步建议等特定信息。M77 在 M76 基础上增加这些字段，输出可直接复制给新 AI 窗口的接手摘要。

## 决策 1：基于 M76 构建，增加窗口接手字段
**选择**：ThreadHandoffSummaryService 组合 ProjectProfile、ContextCompaction，新增 workspace_dir、head_state、origin_state、active_prohibitions、required_docs、unresolved_risks。

**理由**：
- 复用 M76 的压缩能力
- 新窗口接手需要 Git 状态和禁止事项等特定信息
- 文档明确字段要求

## 决策 2：明确声明禁止事项
**选择**：active_prohibitions 包含 9 条硬禁止事项，在 Markdown 开头显眼位置展示。

**理由**：
- 新窗口 AI 可能不熟悉项目规则
- 前置禁用声明比后置规则描述更有效
- 对齐 Claude Code 的 System Prompt 注入理念

## 风险
- Head/origin 状态依赖 git 命令可用性
- 未解决风险提取自 project-state，可能不完全
