# M72 Code Map Index — 执行计划

## 目标
建立最小代码地图索引，让 Agent 知道主要模块职责和入口。不做大规模语义索引，不引入重型依赖。

## 参考资料
| # | 文件 | 采用原则 |
|---|------|---------|
| 1 | `20260628_上下文工程_Context_Engineering.md` | 上下文按需加载——CodeMap 提供索引，实际内容在需要时才读取 |
| 2 | `GBrain学习笔记.md` | 代码结构理解作为 Agent 上下文的一部分，不做重型语义分析 |
| 3 | `桌面AI编程Agent全流程架构对比.md` | 第 4 层上下文引擎：文件索引是项目感知的基础 |

## 范围
- 新增 `CodeMapIndexService`：静态文件级索引
- 索引范围：`services/agent-core/src/bolt_core`、`services/agent-core/tests`、`apps/desktop/src`、`packages/shared/src`
- 排除：node_modules、dist、build、缓存、venv、证书、secret、.bolt、uv.lock
- 查询：list、query by keyword、filter by category、get file summary
- 静态解析：Python AST、TS regex，不 import、不执行

## 产出文件
- `services/agent-core/src/bolt_core/code_map_index.py`
- `services/agent-core/src/bolt_core/code_map_index_api.py`
- `services/agent-core/tests/test_code_map_index.py`
- 修改 `app.py` 注册 router
- `docs/exec-plans/active/072-code-map-index.md`（本文件）
- `docs/decisions/072-code-map-index.md`
- `docs/phase-72-review-gate.md`

## 验收标准
- [x] 能列出核心入口
- [x] 能按关键词查到相关文件
- [x] 能说明"代码地图只是只读上下文，不授予执行权限"
- [x] tests 覆盖索引、过滤、查询、忽略目录、secret path 排除
- [x] 不执行代码，不 import 项目模块来反射
- [x] 不读取超大无关目录
