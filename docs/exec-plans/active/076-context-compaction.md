# M76 Context Compaction + M77 Thread Handoff Summary — 快速执行计划

## M76 Context Compaction
将各记忆层数据压缩为结构化摘要，支持 token budget / max_items。

## M77 Thread Handoff Summary
基于 M76 输出，生成新窗口接手摘要（Markdown + JSON）。

## 实现
| 文件 | 用途 |
|------|------|
| `context_compaction.py` | ContextCompactionService |
| `context_compaction_api.py` | API router |
| `thread_handoff_summary.py` | ThreadHandoffSummaryService |
| `thread_handoff_summary_api.py` | API router |
| 各 tests | 2 × test files |
| `app.py` | 注册 2 个 routers |
