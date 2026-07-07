# M73 Decision Memory — 执行计划

## 目标
建立决策记忆层，让 Biot 从 `docs/decisions/*.md` 中理解"为什么这么做"，而不是只知道代码现状。

## 参考资料
| 文件 | 采用原则 |
|------|---------|
| `E:\BinCloud\知识库\03-知识\AI工程\20260628_上下文工程_Context_Engineering.md` | 记忆分层（短期/长期/工作区）、上下文隔离原则、Pinned Facts |
| `E:\BinCloud\知识库\03-知识\AI工程\轻量级智能体记忆设计.md` | 轻量结构化模板 > 向量库、Tag路由精准检索、四维度模板（目标/方案/结果/痛点） |
| `E:\BinCloud\知识库\03-知识\AI工程\GBrain学习笔记.md` | 合成层（给答案不给片段）、缺口分析（明确标记未知）、知识图谱自布线 |
| `docs/桌面AI编程Agent全流程架构对比.md` | 第4层上下文引擎定位：项目感知、文件索引、对话压缩、记忆系统 |

核心设计原则：
- 轻量优先：静态文件解析，不引入向量库/LLM
- 结构化模板：每条决策固定字段，可索引可追溯
- source_refs 必保留：每个结论穿透回原始文件
- 只读：不自动写入新决策

## 实现文件
| 文件 | 用途 |
|------|------|
| `services/agent-core/src/bolt_core/decision_memory.py` | DecisionMemoryService + DecisionRecord dataclass |
| `services/agent-core/src/bolt_core/decision_memory_api.py` | FastAPI router (5 endpoints) |
| `services/agent-core/tests/test_decision_memory.py` | Service tests |
| `services/agent-core/tests/test_decision_memory_api.py` | API tests |
| `services/agent-core/src/bolt_core/app.py` | 注册 router |

## API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/decisions` | 列出所有决策（摘要列表） |
| GET | `/decisions/{decision_id}` | 获取单条决策详情 |
| GET | `/decisions/query` | 按 milestone/keyword 查询 |

## 验收标准
- [ ] 能列出 M55-M72 已有 decision（至少 60+ 条）
- [ ] 能查询 M70/M71/M72 决策
- [ ] 每条 decision 有 source_refs
- [ ] 缺失/格式异常文档时中文降级，不崩
- [ ] 不读取 secret、证书材料
- [ ] 不新增自动执行入口
- [ ] targeted tests 全部通过
