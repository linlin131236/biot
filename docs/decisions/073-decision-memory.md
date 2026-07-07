# M73 Decision Memory — 设计决策

## 决策背景
Biot 已经到了 M72，docs/decisions/ 目录下有 60+ 条设计决策记录。但当前系统只能逐文件读取，无法结构化查询。M73 让 Agent 能理解"为什么这么做"，而不是只知道代码现状。

## 决策 1：静态文件解析，不引入 LLM
**选择**：纯 Markdown 解析器从 `docs/decisions/*.md` 提取结构化字段。

**理由**：
- 决策文档已经存在，不需要额外生成
- 静态解析确定性高、速度快、无 API 成本
- 对齐 Context Lakehouse 原则：source_refs 指向原始文件
- 参考《轻量级智能体记忆设计》"轻量结构化方案"优于"盲目堆向量库"

## 决策 2：固定字段模型
**选择**：DecisionRecord 包含 8 个固定字段：decision_id, milestone, title, summary_cn, rationale, tradeoffs, outcome, source_refs。

**理由**：
- 轻量级智能体记忆设计推荐 Tag 路由 + 固定模板
- 字段覆盖"为什么这么设计"的核心信息
- summary_cn 支持快速浏览，不把整篇文档塞给 LLM

## 决策 3：解析器容错降级
**选择**：格式异常或缺失的文档返回降级记录（中文提示），不崩溃。

**理由**：
- 决策文档格式不统一（早期简单格式，后期结构化格式）
- Agent 工作流不应因文档格式问题中断
- GBrain 的"缺口分析"理念：明确标注"不知道什么"

## 决策 4：只读，不自动写入
**选择**：DecisionMemoryService 无写方法，API 无 POST/PUT/DELETE。

**理由**：
- 文档明确："默认只读，不自动写入新决策"
- 决策应由人工在 docs/decisions/ 中维护
- 防止 Agent 自动产生不可审计的决策

## 风险
- 解析器覆盖了大多数格式，但极端自由格式可能提取不完整
- 检索精度依赖 Markdown 解析质量，不保证语义匹配
- milestone 提取依赖文件名前缀，非标准命名可能解析失败
