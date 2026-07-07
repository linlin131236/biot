# 桌面 AI 编程 Agent 全流程架构对比

> Claude Code × Codex CLI × Hermes Agent × Biot
> 2026-07-07 调研整理

---

## 一、四者定位

| 产品 | 定位 | 开源 | 核心理念 |
|------|------|------|---------|
| **Claude Code** | 商业 AI 编程助手 | ❌ 闭源 | 安全第一，用户掌控，精细权限 |
| **Codex CLI** | OpenAI 命令行编程 Agent | ✅ 开源 | 速度优先，自主执行，sandbox 兜底 |
| **Hermes Agent** | 通用自进化 Agent 框架 | ✅ 开源 | 学习闭环，跨平台，多模型自由 |
| **Biot** | 本地桌面安全编程 Agent | ❌ 自研 | Claude 的安全 + Codex 的流畅 |

---

## 二、完整产品分层架构

一个完整的桌面 AI 编程产品，从上到下共 7 层：

```
第 7 层：产品体验 ─── 首次向导、工作区、模型配置、权限面板、轨迹可视化、快捷键
第 6 层：任务编排 ─── Plan 模式、子代理分发、自主多步循环、暂停恢复、定时任务
第 5 层：执行引擎 ─── 工具调度、权限门控、文件变更管理、Shell 沙箱、失败分类重试
第 4 层：上下文引擎 ─── 项目感知、文件索引、对话压缩、记忆系统、System Prompt 注入
第 3 层：Agent 大脑 ─── LLM Gateway、Prompt 构建、Tool Call 解析、验证器、MOA
第 2 层：安全底座 ─── 路径防护、权限队列、执行审计、恢复策略、密钥管理
第 1 层：基础设施 ─── 桌面壳、Agent Core、共享协议、测试体系、打包发布
```

---

## 三、Claude Code 架构

### 核心 Agent Loop

```
用户输入
  → System Prompt 注入（CLAUDE.md + memory + hooks + tools schema）
  → Agent Loop 启动
      ├─ 理解意图（LLM 推理当前状态）
      ├─ 感知环境（Read / Glob / Grep / git log 扫项目）
      ├─ 决策行动（选择合适的 tool + 参数）
      ├─ 执行（Bash / Write / Edit / Agent）
      ├─ 观察结果（tool output → 下一轮 context）
      └─ 循环直到任务完成
  → 权限控制（auto-allow / ask / deny，per-tool + per-scope）
  → 上下文管理（自动压缩长对话 + 三层 memory 持久化）
  → 子任务分发（Agent 工具 spawn 子代理并行干活）
  → Plan 模式（先出计划，批准后再执行）
  → 任务追踪（TaskCreate → in_progress → completed）
```

### 关键数据流

```
Tool Request → Permission Check → Execute → Trace Record → Tool Result → Next Context
```

### 亮点

1. **多层 Context 注入** — CLAUDE.md（项目规则）+ hooks（自定义行为）+ memory（跨会话持久化）+ system prompt（工具定义），四层叠加形成完整的 agent 世界观
2. **Plan 模式** — 写代码前先出计划，用户批准后再执行，避免方向性浪费
3. **Worktree 隔离** — 每次修改在独立 git worktree 中完成，互不干扰
4. **20+ 工具原子化** — Read / Write / Edit / Bash / Glob / Grep / Agent / Task / WebSearch / WebFetch 等，分工明确
5. **会话管理（CCD）** — 多 session 并行 + 搜索历史 + 归档

### 弱点

1. 不开源，定制能力有限
2. 模型绑定 Anthropic，不能自由切换
3. 无自学习能力 — 技能不会自动沉淀

---

## 四、Codex CLI 架构

### 核心 Agent Loop

```
用户输入
  → SDK Agent 初始化（配置 model + tools + instructions）
  → 自主 Loop（默认不打断）
      ├─ LLM 推理
      ├─ 工具选择（file ops + shell + search + web）
      ├─ Sandbox 内执行（隔离环境）
      ├─ 结果回流到 LLM
      └─ 循环直到完成或 token 耗尽
  → 少量权限检查（偏信任模式，sandbox 就是安全边界）
```

### 亮点

1. **速度优先** — sandbox 内的操作默认全自动，不反复问用户
2. **Sandbox 隔离** — 执行环境沙箱化，不污染真实文件系统
3. **开源** — 可以定制、嵌入到自己产品中
4. **SDK 化** — 适合作为能力嵌入其他应用
5. **流式 Token** — 低延迟，实时显示执行过程

### 弱点

1. 安全粒度粗 — sandbox 外没有精细权限控制
2. 上下文管理简单 — 无非 CLAUDE.md、memory 系统、hooks
3. 无 Plan 模式 — 直接开干，方向错了就重来
4. 无子代理 — 单线程执行，不能并行排查

---

## 五、Hermes Agent 架构（重点）

### 核心能力全景

```
Hermes Agent
├─ CLI / TUI — 终端交互界面
├─ Gateway — 多平台接入（Telegram/Discord/Slack/WhatsApp/Signal/Email）
├─ Desktop App — Electron 桌面应用
├─ Agent Core
│   ├─ conversation_loop.py — 对话循环（3900行，从 run_agent 抽离）
│   ├─ context_engine.py — 上下文引擎
│   ├─ prompt_builder.py — Prompt 构建
│   ├─ tool_executor.py — 工具执行
│   ├─ tool_guardrails.py — 工具护栏
│   └─ error_classifier.py — 错误分类 + 自动重试
├─ 自进化系统
│   ├─ learning_graph.py — 学习图谱（技能节点 + 记忆节点 + 关联边）
│   ├─ skill creation — 复杂任务后自动创建技能
│   ├─ skill self-improvement — 技能在使用中自我改进
│   └─ curator.py — 定期审查和优化知识
├─ MOA（Mixture of Agents）— moa_loop.py
│   └─ 多代理投票 / 审查 / 合成
├─ 上下文管理
│   ├─ context_compressor.py — 上下文压缩
│   ├─ conversation_compression.py — 对话压缩
│   ├─ trajectory_compressor.py — 轨迹压缩（1574行，训练数据用）
│   └─ memory_manager.py — 记忆管理（FTS5 搜索 + LLM 摘要）
├─ 多模型支持
│   ├─ Anthropic / OpenAI / DeepSeek / NVIDIA / 小米 MiMo / GLM / Kimi / MiniMax
│   ├─ 200+ 模型通过 OpenRouter
│   └─ Nous Portal 统一 API
├─ 多后端终端
│   ├─ local / Docker / SSH / Daytona / Singularity / Modal
│   └─ Daytona/Modal 支持 Serverless（空闲休眠，零成本）
├─ 语音
│   ├─ STT（faster-whisper / Groq Whisper / OpenAI Whisper）
│   └─ TTS（Edge TTS / ElevenLabs / OpenAI / MiniMax / NeuTTS）
├─ Cron — 内置定时调度器
├─ ACP（Agent Communication Protocol）— Agent 间通信标准
└─ 用户建模 — Honcho 辩证式用户建模
```

### 核心亮点（别的产品没有的）

1. **自进化技能系统** — Agent 完成复杂任务后**自动创建技能**，下次遇到类似问题直接调用。技能在使用中**自我改进**。这是 Hermes 最独特的能力——代码量增长的同时，agent 的能力也在增长

2. **Learning Graph** — 可视化展示"你学到了什么"：技能节点 + 记忆节点 + 关联边。不是静态文档，是活的图谱

3. **MOA（Mixture of Agents）** — 多代理投票机制。多个 LLM 独立推理，投票决定最终输出。能大幅减少幻觉，但成本高

4. **Gateway 多平台** — 一个 agent 同时跑在 Telegram、Discord、Slack、WhatsApp、Signal、Email 上，跨平台对话连续。你在手机上发消息，后端是同一套记忆和技能

5. **Trajectory Compressor** — 把完整 agent 执行轨迹压缩成训练数据，用于微调自己的工具调用模型。**数据飞轮**

6. **Honcho 用户建模** — 辩证式理解用户：不是简单记住偏好，而是形成对用户的动态模型

7. **Serverless 后端** — Daytona/Modal 支持，agent 闲时休眠，收到消息自动唤醒，几乎零成本运行

8. **完全开源 + 多模型自由** — 不绑定任何服务商，随时切换模型

### 架构精良度

Hermes 是目前我见过设计最成熟的**开源** agent 框架。`conversation_loop.py` 从 `run_agent.py`（6013行）中抽离出 3900 行的对话循环，有完整的：
- 错误分类器（`error_classifier.py`）— API 错误分 10+ 类别，不同类别不同重试策略
- 工具护栏（`tool_guardrails.py`）— 执行前检查，类似 Biot 的 PermissionGate
- 上下文压缩器 — 自动裁剪 + 手动标记 feedback
- 迭代预算（`iteration_budget.py`）— 控制每次对话的 token 消耗
- 重试状态机（`turn_retry_state.py`）— 专门的失败重试管理

---

## 六、四者逐层对比

### 第 7 层：产品体验

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| 首次运行向导 | ✅ | ❌ CLI | ✅ | ✅ |
| 工作区选择 | ✅ | ❌ | ✅ | ✅ |
| 模型配置 UI | ✅ Settings | ❌ 命令行 | ✅ hermes model | ⚠️ 简陋 |
| 权限审批面板 | ✅ 终端弹窗 | ❌ | ✅ ACP 协议 | ✅ PermissionPanel |
| 轨迹可视化 | ✅ | ❌ | ✅ TUI display | ✅ TracePanel |
| 对话历史 | ✅ | ❌ | ✅ 跨平台连续 | ⚠️ 基础 |
| 快捷键/托盘 | ✅ | ❌ | ✅ Desktop | ❌ |
| 语音交互 | ❌ | ❌ | ✅ STT+TTS | ❌ |
| 多平台接入 | ❌ | ❌ | ✅ 6 平台 Gateway | ❌ |

### 第 6 层：任务编排

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| Plan 模式 | ✅ | ❌ | ❌ | ❌ |
| 子代理分发 | ✅ Agent+Workflow | ❌ | ✅ 并行子代理 | ❌ |
| 自主多步循环 | ✅ | ✅ | ✅ | ⚠️ 单步 |
| 暂停/恢复 | ✅ | ❌ | ✅ Session | ⚠️ M62-M66 |
| 定时任务 | ⚠️ Cron | ❌ | ✅ 内置 Cron | ❌ |
| 目标闭环验证 | ❌ | ❌ | ✅ MoA+Verify | ⚠️ TaskClosure |
| Skill 自创建 | ❌ | ❌ | ✅ | ❌ |

### 第 5 层：执行引擎

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| 工具调度 | ✅ | ✅ | ✅ | ✅ |
| 权限门控 | ✅ 细粒度 | ❌ 粗 | ✅ guardrails | ✅ PermissionGate |
| 文件 diff 管理 | ✅ Edit+patch | ✅ | ✅ | ✅ PatchEngine |
| Shell 沙箱 | ❌ | ✅ Sandbox | ✅ Docker/Modal | ⚠️ ShellExecutor |
| 失败分类重试 | ⚠️ 基础 | ⚠️ 基础 | ✅ error_classifier | ⚠️ FailureMemory |
| Web 搜索 | ✅ | ✅ | ✅ | ✅ |

### 第 4 层：上下文引擎

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| 项目感知 | ✅ Glob/Grep/git | ⚠️ 基础 | ✅ 文件扫描 | ✅ PerceptionService |
| 文件索引 | ✅ Glob | ⚠️ | ✅ | ⚠️ file_indexer |
| 对话压缩 | ✅ 自动 | ❌ | ✅ compressor | ⚠️ context_compressor |
| 多层记忆 | ✅ 三层 | ❌ | ✅ Honcho+Memory | ✅ MemoryStore |
| System Prompt | ✅ CLAUDE.md+hooks | ❌ | ✅ config+skills | ❌ |
| 用户模型 | ⚠️ memory | ❌ | ✅ Honcho 辩证 | ❌ |

### 第 3 层：Agent 大脑

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| LLM Gateway | ⚠️ 仅 Anthropic | ⚠️ 仅 OpenAI | ✅ 20+ provider | ✅ ModelGateway |
| Prompt 构建 | ✅ | ✅ | ✅ prompt_builder | ⚠️ context_builder |
| Tool Call 解析 | ✅ | ✅ | ✅ | ✅ AgentLoop |
| 验证器 | ⚠️ 隐式 | ❌ | ✅ verify_hooks | ✅ Verifier |
| MOA 投票 | ❌ | ❌ | ✅ moa_loop | ❌ |
| 代码审查集成 | ✅ code-review | ❌ | ✅ background_review | ⚠️ review_gate |
| 轨迹压缩（训练用） | ❌ | ❌ | ✅ trajectory_compressor | ❌ |

### 第 2 层：安全底座

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| 路径防护 | ⚠️ 无独立模块 | ⚠️ sandbox | ✅ file_safety | ✅ PathGuard |
| 权限队列 | ✅ | ❌ | ✅ | ✅ PermissionQueue |
| 执行审计 | ✅ Trace | ❌ | ✅ trajectory | ✅ TraceLog |
| 恢复策略 | ⚠️ 手动 | ❌ | ✅ session resume | ⚠️ RecoveryPolicy |
| 密钥管理 | ✅ 不落地前端 | ✅ env | ✅ credential_pool | ✅ Agent Core |
| 敏感文件拒绝 | ❌ | ❌ | ✅ file_safety | ✅ secret_names |
| SSL 证书验证 | ✅ | ✅ | ✅ ssl_guard | ❌ |

### 第 1 层：基础设施

| 能力 | Claude Code | Codex CLI | Hermes | Biot |
|------|:-----------:|:---------:|:------:|:----:|
| 桌面 App | ✅ Electron | ❌ | ✅ Electron | ✅ Electron |
| 后端语言 | Rust/TS | TypeScript | Python | Python |
| 共享协议 | ❌ | ❌ | ACP 协议 | ✅ @bolt/shared |
| 测试覆盖 | ✅ | ⚠️ | ✅ | ✅ 786 tests |
| 打包发布 | ✅ | ❌ | ✅ | ⚠️ |
| 自动更新 | ✅ | ❌ | ✅ | ❌ |
| Serverless | ❌ | ❌ | ✅ Daytona/Modal | ❌ |

---

## 七、Biot 能从每个产品学什么

### 从 Claude Code 学

1. **System Prompt 注入机制** — CLAUDE.md + hooks 是最优雅的"给 agent 注入规则"方案。Biot 需要等效的 `AGENTS.md` 读取 + 注入
2. **Plan 模式** — 写代码前先出计划，用户批准再执行。这在"信任但验证"的安全框架中特别重要
3. **Sub-agent 编排** — Agent 工具 + Workflow 让复杂任务能并行分解

### 从 Codex CLI 学

4. **自主连续执行** — 安全护栏是 Biot 的优势，但护栏太密就变成牢笼。Codex 证明了"默认信任 + sandbox 兜底"是可行的产品策略
5. **低延迟流式** — 用户在等的时候每一步都要实时可见

### 从 Hermes 学（最多可学）

6. **自进化技能系统** — Biot 修复过的 bug、踩过的坑、验证过的模式，为什么不能自动沉淀成 skill？Hermes 的 learning_graph 是这件事的完整实现
7. **Error Classifier** — Hermes 的 `error_classifier.py` 对 API 错误分 10+ 类，不同类别不同策略。Biot 的 FailureMemory 只记录了失败，没有分类和差异化重试
8. **MOA 投票** — 对安全敏感操作（写文件、执行命令），用另一个模型验证一遍会更安全
9. **Gateway 多平台** — 最终产品不应该是"打开桌面 app 才能用"，Telegram/微信上发消息也能控制 agent
10. **Trajectory Compressor** — 长期来看，Biot 产生的执行轨迹是最宝贵的训练数据
11. **Honcho 用户模型** — 理解用户比记住规则更重要

---

## 八、Biot 全流程验收标准

当 Biot 完成 M62-M66 + 以下补齐后，"一句话端到端"应该是：

```
用户说："帮我把 app.tsx 里所有 any 类型替换成具体类型"

Biot 执行流程：
  1. plan 模式 → 分析范围、列出受影响的类型、估算工作量
  2. 用户批准计划
  3. 自动 loop：
     a. Grep 找到所有 `: any` 出现位置
     b. Read 每个文件，推断具体类型
     c. Edit 逐个替换
     d. 每次写完运行 tsc --noEmit 验证
     e. 编译失败 → 自动分析 → 修正 → 再编译
  4. 全部通过后 → 汇报结果 + 记录此次经验为 skill
  5. 下次遇到类似问题，直接复用 skill
```

---

## 九、结论

Biot 的差异化定位是正确的：**Claude Code 的安全粒度 + Codex 的自主流畅 = "信任但验证"**

但差距也很清楚：
- **短期（M62-M66）**：补自主多步循环 + 暂停恢复 + 失败分类
- **中期**：加 Plan 模式 + System Prompt 注入 + 子代理
- **长期**：学 Hermes 的自进化技能系统 + Gateway 多平台 + MOA 投票

Hermes 是当前最优参考对象——它是这四个产品中唯一集齐了"安全、自主、自进化、多模型、多平台"全部能力的。
