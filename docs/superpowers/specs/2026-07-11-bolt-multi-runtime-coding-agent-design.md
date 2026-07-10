# Bolt 多运行时桌面编码 Agent 总体设计

- 日期：2026-07-11
- 分支：`feat/safe-controlled-beta`
- 状态：已由用户批准
- 目标：在保留 Bolt 现有安全桌面底座的前提下，通过 ACP 接入 Hermes，并逐步形成可接 Bolt Core、Hermes、Codex、OpenCode 的统一桌面编码 Agent。

## 1. 背景与调研结论

Bolt 已具备 Electron 桌面端、Python Agent Core、本地文件工具、补丁审批、终端服务、任务状态、上下文压缩原型、记忆模块、OpenAI-compatible 模型网关、Windows Credential Manager、Core 启动身份证明和 Windows 安装包。当前主要差距不是“有没有类名或面板”，而是持久化、真实运行时接入、长任务恢复、统一主流程、MCP、强制沙箱和玩家发布证据。

本设计调研了以下官方开源仓库：

- OpenAI Codex：<https://github.com/openai/codex>，Apache-2.0
- Cline：<https://github.com/cline/cline>，Apache-2.0
- goose：<https://github.com/aaif-goose/goose>，Apache-2.0
- OpenHands：<https://github.com/OpenHands/OpenHands>，核心 MIT，`enterprise/` 除外
- Aider：<https://github.com/Aider-AI/aider>，Apache-2.0
- Continue：<https://github.com/continuedev/continue>，Apache-2.0
- OpenCode：<https://github.com/anomalyco/opencode>，MIT
- Mem0：<https://github.com/mem0ai/mem0>，Apache-2.0
- Agent Client Protocol：<https://github.com/agentclientprotocol/agent-client-protocol>，Apache-2.0
- Hermes Agent：<https://github.com/NousResearch/hermes-agent>，MIT

Hermes 源码调研固定在当时的上游提交 `291eae63b7d37129661082e23df35804c5e89365`。已检查仓库树和关键源码，包括：

- `apps/desktop/`：Electron + React 桌面端、安装、终端、文件、Diff、更新
- `acp_adapter/`：ACP Server、会话、权限、事件和工具映射
- `agent/memory_manager.py` 与 `agent/memory_provider.py`：可插拔记忆生命周期
- `agent/context_engine.py`、`agent/context_compressor.py`、`agent/conversation_compression.py`：上下文预算与压缩
- `agent/skill_commands.py`、`agent/skill_preprocessing.py`：技能加载与记忆污染防护
- `providers/` 与模型 adapter：多供应商接入
- `tools/terminal_tool.py`、`tools/process_registry.py`：持久终端与后台进程
- `hermes_cli/checkpoints.py`、worktree 和 Diff 相关实现

该调研是架构与关键源码级检查，不等于对 Hermes 六千余文件逐行安全审计。任何复制进入 Bolt 的代码仍须逐文件审查、测试和登记来源。

## 2. 选定方案

采用“Bolt 控制台 + 多 Agent Runtime”方案：

```text
Bolt Desktop
  -> Electron Main 安全桥
  -> Bolt Agent Core 控制平面
      -> Bolt Native Runtime
      -> Hermes ACP Runtime（第一外部运行时）
      -> Codex Runtime（后续）
      -> OpenCode Runtime（后续）
```

明确不采用：

- 整仓 Fork Hermes 后换皮
- 删除或推翻 Bolt 现有 Agent Core
- 同时接入多个外部运行时
- 第一阶段引入消息平台、Cron、云端执行和任意第三方插件
- 通过 PATH 静默查找并运行同名程序
- 把真实模型 API Key 交给第三方 Runtime

Bolt 是统一界面、安全控制、任务、记忆和审计层；Hermes 是通过 ACP 接入的成熟 Agent Runtime。

## 3. 五大实施板块

### 板块一：控制平面、持久化与开源治理

目标：建立所有后续能力依赖的稳定数据与接口边界。

包括：

- 固定当前 P0 安全基线和可重现构建
- 建立 `THIRD_PARTY_NOTICES.md` 与上游源码登记
- 定义 `AgentRuntime`、`RuntimeCapabilities`、`RuntimeEvent`、`RuntimeSession`
- 建立 SQLite WAL 数据库、Schema 迁移和原子事务
- 持久化工作区、会话、消息、任务、事件、Checkpoint 和模型非敏感配置
- API Key 继续仅保存在 Windows Credential Manager
- 数据库完整性检查、备份、恢复和损坏时只读降级

完成门禁：配置和任务跨重启恢复；数据库不含 Secret；现有后端、Desktop、P0 和架构测试无回退。

### 板块二：Hermes ACP Runtime 与模型代理

目标：让 Bolt 在不复制 Hermes 主循环的情况下真实驱动 Hermes 完成编码任务。

包括：

- Runtime Manager 和进程生命周期
- `BoltNativeRuntime` 适配
- `HermesAcpRuntime`、ACP 握手、消息、工具、计划、权限、取消和恢复
- Hermes 固定版本、固定路径、SHA-256、协议版本和隔离 HOME
- 外部 Runtime 崩溃、超时、心跳、子进程清理
- 本地 Model Gateway 和每个 Runtime 的临时 Token
- OpenAI-compatible、OpenRouter、中转站、Ollama、LM Studio
- 后续原生 Anthropic 与 Gemini adapter
- 模型能力表、连接测试、Token/费用、限流和错误归一化

完成门禁：Hermes 真实 ACP 子进程在 Bolt 中完成只读任务和一次经审批的命令；真实 API Key 不进入 Runtime 环境、日志或数据库；Runtime 退出后 Token 失效。

### 板块三：长期记忆、上下文、技能与任务恢复

目标：让 Bolt 跨进程、跨 Runtime 和跨会话记住稳定事实并恢复长任务。

包括：

- `MemoryProvider` 生命周期
- 首个生产实现 `LocalSQLiteMemoryProvider`
- 用户偏好、项目事实、架构决策、失败经验、操作流程和任务结果
- FTS5、工作区过滤、时间衰减、重要度和召回原因
- Bolt 作为唯一长期记忆来源；第一阶段关闭 Hermes 外部长期记忆插件
- 会话快照、Runtime session 映射和结构化恢复上下文
- Token 预算、70%～75% 压缩阈值、保护头尾消息和工具输出外置
- 压缩失败不破坏旧上下文
- `SKILL.md` 索引、按需加载、来源、哈希、权限和安全扫描
- 技能自改只能形成 Diff 提案，经批准和失败回放后激活
- Runtime 崩溃恢复；同一任务连续三次崩溃后停止自动恢复

完成门禁：任务和记忆跨重启存在；不同工作区隔离；删除记忆后不再召回；强杀 Hermes 后能从 Bolt Checkpoint 恢复；Secret 不进入记忆。

### 板块四：安全编码工作台、Worktree、Diff、终端与 MCP

目标：形成成熟编码 Agent 的安全修改闭环和受控扩展体系。

包括：

- 每个执行任务使用 Git worktree
- 原工作区 dirty 检查、冲突检测、应用和回滚
- 文件变化事件、并排/行内 Diff、逐文件和逐 Hunk 审核
- Checkpoint 与恢复
- Xterm + PTY 持久终端、Agent 终端和用户终端分离
- 后台进程跟踪、取消和子进程清理
- 只读、工作区写入、完全访问三级沙箱
- Windows Restricted Token、Job Object、ACL、隔离 HOME/TEMP 和网络限制
- 若强制沙箱不可用，执行模式默认退回只读，不得假绿
- 官方 MCP Python SDK、STDIO、Streamable HTTP、Server 身份和逐工具授权
- MCP 输出视为不可信数据，防提示注入、SSRF、Schema 炸弹、超大响应和残留进程
- 第一阶段只开放 Skill；任意第三方 Plugin 不得加载到 Electron Main 或 Agent Core 主进程

完成门禁：原工作区在执行期间不变化；冲突时不覆盖；取消后无残留进程；Hermes/MCP 不能访问工作区外路径或绕过权限；Packaged E2E 使用真实子进程通过。

### 板块五：桌面产品化、真实任务、八维审查与 Windows 发布

目标：把后台能力收敛成普通用户可理解的产品，并用真实证据决定是否发布。

包括：

- 首次启动、模型连接、Runtime 安装、项目打开
- 对话、计划、执行三模式
- Runtime/模型/模式选择器
- 真实 Agent 状态、计划、工具活动、权限、Diff、终端、文件、记忆和技能中心
- 完成页必须展示文件、测试、未运行项目、风险、费用和记忆写入
- 不显示内部 Core URL、端口和 Token
- 不使用定时器制造假进度或假成功
- 建立至少 20 个真实编码任务基准
- 目标：完成率不低于 80%，修改后测试通过率不低于 90%，越权与 Secret 泄露为 0，错误声称完成为 0
- 每个切片执行架构、身份、凭据、隔离、并发恢复、数据一致性、测试真实性和发布风险八维审查
- Windows 签名、`signtool verify /pa`、SBOM、许可证、Secret/ASAR 扫描、干净 Windows 完整 E2E 和 Release Evidence

完成门禁：全量测试通过；20 个真实任务达到指标；无未修 Critical；签名和干净 Windows 安装/任务/退出/卸载 E2E 通过；只有用户明确授权才分发。

## 4. 统一桌面体验

默认界面保持简洁对话；开始执行后自动展开 Agent 状态、计划、工具、权限、Diff、终端和审计。主流程固定为：

```text
打开项目
-> 描述任务
-> 计划
-> 用户批准
-> 建立 worktree
-> Runtime 执行
-> 工具/权限/测试实时显示
-> Diff 审核
-> 应用或丢弃
-> 任务总结
-> 写入经策略过滤的记忆
```

视觉继续采用已批准的深色液态玻璃方向，但光效只服务于状态层级；红色仅表示真实危险；避免宣传页式大标题和无意义 AI 渐变。

## 5. 安全不变量

- Renderer 不持有真实凭据、Core URL、内部端口控制权或可执行程序路径。
- 外部 Runtime 默认不可信，必须使用固定身份、固定版本、哈希、能力表和隔离目录。
- Runtime 不读取 Credential Manager，只获得短期、限权、可撤销的模型代理 Token。
- 所有 Runtime 工具和权限统一映射到 Bolt 控制平面。
- Shell、MCP、Skill 和工具输出均是不可信输入。
- 工作区写入必须有真实 OS 强制边界，不能只靠提示词。
- 任何上游代码复制都登记仓库、路径、Commit、许可证和本地修改，并保留通知。
- 不复制 Claude Code 闭源代码，不复制 OpenHands `enterprise/`。
- 同一安全问题连续失败三次，停止局部补丁并返回设计。

## 6. 执行纪律

每个板块严格按顺序执行。每个 Task 使用：

```text
读取 Spec 与现状
-> 写失败测试
-> 运行确认 RED
-> 最小实现
-> 运行确认 GREEN
-> 相关回归
-> 架构门禁
-> 对抗审查
-> 独立质量审查
-> 提交
-> 下一 Task
```

禁止删除测试、降低断言、增加无理由 skip/todo/only、用 Mock 冒充最终真实子进程、自动 Push、自动发布或清理用户未跟踪文件。

## 7. 时间与里程碑

- 第 1～2 周：持久化与 Runtime Contract
- 第 3～4 周：Hermes ACP 可在 Bolt 内真实运行
- 第 5～6 周：模型代理、长期记忆和恢复
- 第 7～8 周：Worktree、Diff、终端和强制沙箱
- 第 9～10 周：MCP、技能和桌面主流程
- 第 11～12 周：20 个真实任务与可靠性修复
- 第 13～14 周：签名、干净 Windows 和发布证据

爸爸个人真实试用可以在 Hermes 纵向切片和持久化完成后开始；玩家内测必须等全部发布门禁通过。

## 8. 决策结论

Bolt 不做 Hermes 换皮，也不重复手写所有成熟 Agent 能力。Bolt 的差异化是：

- 统一桌面体验
- 多 Runtime
- 多模型和中转站
- 长期记忆
- 强权限与审计
- Worktree 安全修改
- 中文用户友好
- Runtime 可替换，不被单一供应商锁定

第一外部 Runtime 固定为 Hermes ACP。只有该纵向切片完成并通过真实 E2E 后，才允许规划 Codex/OpenCode Runtime。
