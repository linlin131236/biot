# M80 Memory Dogfood — 执行计划

## 目标
M71-M80 大复盘门。验证 V3 项目理解与长期记忆是否达标，是否能让新窗口更稳地接手项目。

## 参考资料
- 所有 M71-M79 实现代码和测试
- `docs/桌面AI编程Agent全流程架构对比.md` — 上下文引擎层验收标准
- `docs/project-state.md` — 硬规则和安全要求

## 实现文件
| 文件 | 用途 |
|------|------|
| `services/agent-core/src/bolt_core/memory_dogfood.py` | MemoryDogfoodService（12 项就绪度检查） |
| `services/agent-core/src/bolt_core/memory_dogfood_api.py` | API router |
| `services/agent-core/tests/test_memory_dogfood.py` | Service tests |
| `docs/phase-80-review-gate.md` | 大复盘审查门 |
| `docs/decisions/080-memory-dogfood.md` | 设计决策 |
| `services/agent-core/src/bolt_core/app.py` | 注册 router |

## 验收标准
- [x] M80 review gate 明确：V3 记忆层是否允许进入 M81
- [x] 12 项检查全部通过
- [x] 不新增自动执行、自动 approve、自动 push
- [x] 不进入 M81
