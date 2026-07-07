# Bolt Knowledge Source Index

## 目的
把 `E:\BinCloud` 里的课程和知识库材料，映射到 Bolt/Biot 的长期产品路线。后续每个 milestone 开工前，只读对应 2-4 篇材料，避免乱翻整个知识库，也避免把无关课程塞进上下文。

## 使用原则
- 只引用和当前 milestone 直接相关的材料。
- 先读深度笔记，再读长课正文；除非遇到设计分歧，不默认加载超长课程全文。
- 课程材料只作为设计参考，最终实现仍以 Bolt 现有代码、测试和安全规则为准。
- 不把课程内容直接复制进产品代码或 prompt；只提炼架构原则、验收标准和风险清单。
- 对安全、权限、执行、记忆相关内容，优先选可测试、可审计、可回滚的方案。

## 第一优先：直接支撑 Bolt 架构

### Agent 工作流核心，M61-M70
推荐资料：
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase14-Agent工程-深度笔记-上.md`
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase14-Agent工程-深度笔记-下.md`
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_AgentHarness20层进化指南.md`
- `E:\BinCloud\知识库\03-知识\AI开源项目分析\Superpowers开源项目分析.md`

引用方式：
- M61-M62：提取 Agent Loop、状态机、停止条件、轮次预算。
- M63-M65：提取工具选择策略、失败分类、安全重试。
- M66-M70：提取长任务暂停/恢复、human steering、dogfood 标准。

不要引用：
- 不直接照搬框架设计。
- 不为了像某个框架而重构 Bolt 现有闭环。

### 工具与协议，M101-M112
推荐资料：
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase13-工具与协议-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\AI工程\20260629_Agent开发技术栈_MCP_Skills_LangGraph.md`
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_MCP_A2A_协议标准化.md`

引用方式：
- M101-M102：Tool Registry、schema validator、工具声明三要素。
- M103-M110：只读工具、副作用工具、权限分级、MCP/A2A 边界。
- M111-M112：工具 eval 和工具生态 dogfood。

关键落点：
- 工具必须有 schema。
- 有副作用工具必须 PermissionGate。
- 工具输出是不可信输入，不能直接变成指令。

### 上下文工程与 Context Lakehouse，M71-M80
推荐资料：
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_上下文工程_Context_Engineering.md`
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_Karpathy_LLM_Wiki_知识库新范式.md`
- `E:\BinCloud\知识库\03-知识\AI工程\GBrain学习笔记.md`
- `E:\BinCloud\知识库\03-知识\AI工程\轻量级智能体记忆设计.md`

引用方式：
- M71：Context Data Model，定义 raw/staging/clean/result/lineage。
- M72-M74：Raw Event Store、Cleaning Pipeline、SQL Memory Layer。
- M75-M77：Lineage Traceback、Context Budget Query API、Memory Debug UI。
- M78-M80：memory permission boundary、memory search、memory dogfood。

架构原则：
- 原始数据只追加。
- 清洗逻辑可复现。
- 分析代码默认只读 SQL 清洗层。
- 每个结论必须能穿透回 raw/log/evidence。

## 第二优先：安全、评估、生产化

### 安全底座，M55-M60、M124
推荐资料：
- `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`
- `E:\BinCloud\知识库\03-知识\AI工程\AI安全与对齐全景.md`
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase18-伦理安全对齐-深度笔记.md`

引用方式：
- M55：审计文件完整性和损坏诊断。
- M56：证据脱敏和 secret 防泄露。
- M57：release readiness gate。
- M124：隐私、安全、供应链和权限总审计。

重点检查：
- prompt injection。
- 工具链权限。
- MCP/A2A 供应链。
- secret/token/cert 泄露。
- 自动执行和自动批准路径。

### 长期模型内部监控与对齐研究，M113-M120、M124+
推荐资料：
- `docs/references/anthropic-jlens-global-workspace-2026.md`

引用方式：
- M113-M120：作为模型能力评估、内部状态监控、智能 dogfood 的长期研究参考。
- M124+：作为安全审计、恶意意图检测、对齐风险解释的研究参考。

可提炼原则：
- 不只看最终输出，也要关注模型中间意图、评估意识和安全相关内部状态。
- "只读审计，不直接执行"仍是 Biot 当前安全哲学；内部监控只能作为额外风险信号，不能替代 PermissionGate。
- 如果未来接入开源模型，可评估 J-lens 类机制作为本地安全监控工具，但必须先证明成本、可解释性和误报率可控。
- Counterfactual Reflection Training 可作为未来安全训练/反思机制参考，不应在当前产品代码或 prompt 中照搬论文内容。

暂不采用：
- 当前 M81-M90 多 Agent 骨架不使用此资料作为实现依据。
- 当前不实现 J-lens、Jacobian 计算、GPU 依赖或模型权重相关能力。

### 评估与 benchmark，M117-M120
推荐资料：
- `E:\BinCloud\知识库\03-知识\AI工程\Agent评估方法论.md`
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase17-基础设施与生产-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase19-综合项目-深度笔记.md`

引用方式：
- M117：Evaluation Harness。
- M118：Benchmark Dashboard。
- M119：cost/speed/quality profiles。
- M120：intelligence dogfood。

原则：
- 不靠主观互评。
- 不靠模型自夸。
- 每个智能能力都要有可自动验证的任务集。

### 生产基础设施，M121-M125+
推荐资料：
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase17-基础设施与生产-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\AI工程\AI基础设施与生产部署.md`
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第26章-容错.md`
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第27章-规模化运维.md`
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第30章-安全与隐私.md`

引用方式：
- M121：crash recovery。
- M122：data migration。
- M123：update/rollback。
- M125：public beta readiness。

## 第三优先：多 Agent 和产品化

### 多 Agent 团队，M81-M90
推荐资料：
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase16-多Agent与群体-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\方法论\Loop模式升级版-SkillLearner自动进化.md`
- `E:\BinCloud\知识库\03-知识\AI开源项目分析\2026-06-21 Flock架构分析——AI开发团队流水线设计.md`
- `E:\BinCloud\知识库\03-知识\AI工程\Hermes多Agent团队Profile搭建实战.md`

引用方式：
- M81-M82：Role Protocol、Planner/Builder/Reviewer split。
- M83-M86：Researcher integration、subtask assignment、reviewer gate、conflict resolution。
- M87-M90：status board、SkillLearner、multi-agent recovery、team dogfood。

关键要求：
- Reviewer 不能和 Builder 混成同一个自我批准上下文。
- SkillLearner 只改技能/流程文档，不直接改业务代码。
- 多 Agent 输出必须有证据、测试和审查结果。

### 产品化流水线，M91-M100
推荐资料：
- `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md`
- `E:\BinCloud\知识库\03-知识\方法论\20260628_讨论场到执行系统_ZCode看板法.md`
- `E:\BinCloud\知识库\03-知识\AI工程\OpenClaw实际场景学习报告.md`

引用方式：
- M91-M95：中文任务首页、权限中心、时间线、诊断中心、发布准备页。
- M96-M100：多任务队列、失败解释、会话恢复、设置面板、桌面 Beta dogfood。

产品原则：
- 用户第一屏应该是可用工作台，不是说明页。
- 所有状态必须能解释下一步。
- 失败必须有中文原因和建议动作。

## 暂不优先引用
- 数学基础、经典机器学习、计算机视觉、语音音频：适合作为长期能力背景，不是 Bolt 当前瓶颈。
- 从零造 LLM：除非 M113-M120 进入模型策略和评估，否则不作为实现依赖。
- 多模态 AI：等 M100 以后 UI/工具生态稳定再看。
- 高校公开课：可做背景阅读，不直接绑定 milestone。

## 每组 milestone 的推荐读取量
- M55-M57：读安全/完整性/评估相关 2-3 篇。
- M61-M70：读 Agent 工程深度笔记上下 + Harness 指南。
- M71-M80：读上下文工程 + 记忆设计 + GBrain。
- M81-M90：读多 Agent + SkillLearner + Flock。
- M91-M100：读产品化流水线 + OpenClaw 场景报告。
- M101-M112：读工具与协议 + MCP/A2A。
- M113-M120：读评估方法论 + 模型路由/benchmark。
- M121-M125：读基础设施、容错、安全隐私。

## 后续动作
每次新 milestone 开工前，在 exec plan 里加一个 `参考资料` 小节，列出本次实际读取的 2-4 个文件路径和采用的原则。没有读取就不要声称参考了知识库。
