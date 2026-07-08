# M159 Exec Plan — Researcher Execution Engine

> 当前基线：M158 已完成并 push（99f9d1c）。Researcher 只有 brief/summary 数据验证，不能实际读取代码库。本 milestone 升级为执行引擎。

## 现状分析

### 已有
- `ResearcherIntegrationService`：管理 brief/summary 数据对象，验证 source_refs 数量
- `ResearchScope`：project_docs / bincloud_refs / code_map / decision_memory / failure_memory
- 后端 API：`/research/briefs`、`/research/summaries`、`/research/validate-source-refs`
- 内存层：`memory_store.search()`、`decision_memory.query_by_keyword()`、`failure_memory_index.query_by_keyword()`、`code_map_index.query()`
- 前端：无 Researcher UI

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| Researcher 不执行查询 | P1 | `create_brief`/`produce_summary` 只做数据验证，不查询任何数据源 |
| 无代码地图查询 | P1 | 不能根据 brief 问题搜索代码地图 |
| 无决策/失败记忆查询 | P1 | 不能查询 decision_memory / failure_memory |
| 无项目文档读取 | P2 | 不能读取项目文档文件 |
| 无执行端点 | P2 | 没有 `POST /research/execute` 端点 |
| 无前端展示 | P2 | 桌面端无 Researcher 面板 |

## 执行方案

### 改动 1：ResearcherEngine 执行引擎
**文件**：`services/agent-core/src/bolt_core/researcher_integration.py`（扩展）

新增 `execute_brief(brief_id)` 方法：
- 加载 brief
- 根据 scope 查询对应数据源：
  - code_map → `code_map_index.query(question_keywords)`
  - decision_memory → `decision_memory.query_by_keyword()`
  - failure_memory → `failure_memory_index.query_by_keyword()`
  - project_docs → 读取 docs/ 目录下相关文件（只读）
- 从查询结果中提取 principles_cn / risks_cn
- 生成 source_refs
- 自动调用 `produce_summary()` 提交结果

约束：
- 只读操作，不修改文件
- 最多查询 4 个数据源
- 不执行任何工具
- 不自动审批

### 改动 2：后端 execute 端点
**文件**：`services/agent-core/src/bolt_core/researcher_integration_api.py`

新增 `POST /research/execute` 端点：
- 接收 `brief_id`
- 调用 `service.execute_brief(brief_id)`
- 返回 ResearchSummary 或 ResearchValidation

### 改动 3：前端 API 函数
**文件**：`apps/desktop/src/harnessClientAutonomy.ts`

新增 `executeResearch(briefId)` 函数。

### 改动 4：前端 ResearcherPanel
**文件**：`apps/desktop/src/ResearchPanel.tsx`（新建）

功能：
- 创建 research brief（标题/问题/scope）
- 显示可用 scopes
- 执行 research
- 显示结果（摘要/原则/风险/引用来源）

### 改动 5：前端测试
**文件**：`apps/desktop/src/ResearchPanel.test.tsx`（新建）

### 改动 6：后端测试
**文件**：`services/agent-core/tests/test_researcher_integration.py`（新建或扩展）

新增测试：
- `test_execute_brief_code_map_scope` — 查询代码地图
- `test_execute_brief_decision_memory_scope` — 查询决策记忆
- `test_execute_brief_unknown_brief_returns_validation_error`
- `test_execute_brief_respects_max_sources`

## 验收标准
1. ✅ `POST /research/execute` 能根据 brief 查询数据源并产生 summary
2. ✅ Researcher 不修改文件、不执行工具、不审批
3. ✅ 所有 UI 文案中文
4. ✅ `pnpm run quality` 通过
5. ✅ `git diff --check` 通过
6. ✅ 无 `as any` / `unknown as`
7. ✅ renderer 无危险暴露

## 实施顺序
1. ResearcherEngine 执行引擎（researcher_integration.py）
2. 后端 execute 端点
3. 后端测试
4. 前端 API 函数
5. ResearcherPanel 组件
6. 前端测试
7. quality gates
8. decision + review gate + project-state
9. commit
