# M161 Exec Plan — Reviewer Execution Engine + strict Gate

> 当前基线：M160 已完成并 push（771e8af）。Reviewer 只有 gate 逻辑（ReviewerIndependentGateService 验证预计算的 review package），没有执行引擎。本 milestone 升级为能实际读取 Builder 输出产生审查发现的执行引擎 + strict Gate。

## 现状分析

### 已有
- `ReviewerOutput` dataclass（findings, evidence, tests_status, residual_risks, verdict, source_refs）
- `ReviewerIndependentGateService`：验证预计算的 review package
- `ReviewGate`：checklist 评估（pass/fail）
- `BuilderOutput`：code_changes, tests, evidence_refs, source_refs

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 无 Reviewer 执行引擎 | P1 | 不能根据 Builder 输出扫描风险 |
| 无 strict Gate 自动判定 | P1 | P0/P1/P2 严重性需自动映射到 verdict |
| 无 review endpoint | P1 | 没有 `POST /reviewer/review` |
| 无前端 ReviewerPanel | P2 | 桌面端无审查面板 |

## 执行方案

### 改动 1：ReviewerEngine
**文件**：`services/agent-core/src/bolt_core/reviewer_engine.py`（新建）

- `review_output(builder_output, code_changes)` 扫描 code_changes 中的风险模式
- 风险模式：ipcRenderer(P0), process.(P0), eval(P0), require( P0), as any(P2), unknown as(P2), push/release/tag/delete(P1), subprocess(P1), shell=True(P1)
- strict Gate：P0/P1 → blocked, P2 → changes_requested, 无发现 → approved

### 改动 2：后端 endpoint
**文件**：`services/agent-core/src/bolt_core/reviewer_api.py`（新建）

- `POST /reviewer/review` - 审查 Builder 输出
- `GET /reviewer/verdict/{verdict}` - verdict 中文标签

### 改动 3：前端
- `harnessClientAutonomy.ts`：`reviewBuilderOutput`, `fetchReviewVerdictLabel`
- `ReviewerPanel.tsx`：输入/执行/verdict badge/findings 列表
- `ReviewerPanel.test.tsx`：6 个测试

## 验收标准
1. ✅ ReviewerEngine 扫描 code_changes 风险
2. ✅ strict Gate: P0/P1 → blocked, P2 → changes_requested
3. ✅ 所有 UI 文案中文
4. ✅ `pnpm run quality` 通过
5. ✅ `git diff --check` 通过
6. ✅ 无 `as any` / `unknown as`
7. ✅ renderer 无危险暴露
