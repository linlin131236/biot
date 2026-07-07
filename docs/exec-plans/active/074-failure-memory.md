# M74 Failure Memory — 执行计划

## 目标
建立失败记忆索引，让 Biot 能记住历史失败模式、修复方式、验证命令和复发风险。

## 参考资料
| 文件 | 采用原则 |
|------|---------|
| `E:\BinCloud\知识库\03-知识\AI工程\20260628_上下文工程_Context_Engineering.md` | 记忆分层、68% Agent失败与检索质量有关、上下文隔离 |
| `E:\BinCloud\知识库\03-知识\AI工程\轻量级智能体记忆设计.md` | 四维度模板、Tag路由、SQL精准检索 |
| 现有 `failure_classifier.py` | 8类失败分类对齐 |
| 现有 `failure_memory.py` | ToolFailure/FailureMemory 结构参考 |

## 数据源
- `docs/phase-*-review-gate.md`：P1/P2 修复记录
- `docs/project-state.md`：已知风险
- 现有 `FailureStore` 运行时记录（如有）

## 实现文件
| 文件 | 用途 |
|------|------|
| `services/agent-core/src/bolt_core/failure_memory_index.py` | FailureMemoryIndexService + FailureRecord |
| `services/agent-core/src/bolt_core/failure_memory_index_api.py` | FastAPI router |
| `services/agent-core/tests/test_failure_memory_index.py` | Service tests |
| `services/agent-core/tests/test_failure_memory_index_api.py` | API tests |
| `services/agent-core/src/bolt_core/app.py` | 注册 router |

## 验收
- [ ] 能收录 M57/M60/M66/M67-M72 P1/P2
- [ ] 中文失败解释和修复摘要
- [ ] source_refs 可追溯
- [ ] 不包含 secret
- [ ] 不触发自动修复/自动 retry/自动 approve
