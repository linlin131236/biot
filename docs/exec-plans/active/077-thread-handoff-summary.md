# M77 Thread Handoff Summary — 执行计划

## 目标
基于 M76 ContextCompaction，生成新窗口接手摘要。解决"换窗口不失忆"的产品体验问题。

## 参考资料
- `docs/桌面AI编程Agent全流程架构对比.md` — 第4层上下文引擎：项目感知、文件索引、对话压缩、记忆系统
- M76 Context Compaction 输出

## 数据源
- `docs/project-state.md`：当前状态
- M76 ContextCompaction：压缩上下文
- Git 状态：HEAD、origin 状态

## 实现文件
| 文件 | 用途 |
|------|------|
| `services/agent-core/src/bolt_core/thread_handoff_summary.py` | ThreadHandoffSummaryService |
| `services/agent-core/src/bolt_core/thread_handoff_summary_api.py` | API router |
| `services/agent-core/tests/test_thread_handoff_summary.py` | Service tests |
| `services/agent-core/src/bolt_core/app.py` | 注册 router |

## 验收标准
- [x] 能生成 M73-M80 接手摘要
- [x] Markdown 适合直接复制给新 AI
- [x] JSON 适合前端或 API 使用
- [x] source_refs 完整
- [x] 不进入 M81
- [x] 不包含 secret
- [x] 明确"不自动执行、不自动 push、不进入未授权 milestone"
