# Phase 41 Review Gate

## 状态：审查通过

## 端到端狗粮场景
| 场景 | 验证方式 | 结果 |
|---|---|---|
| 选择工作区 | App.test + dogfood | ✅ |
| 创建 goal | GoalConsole.test | ✅ |
| 启动 run | GoalConsole.test | ✅ |
| agent loop 运行 | GoalConsole.test + test_agent_loop | ✅ |
| timeline/evidence 可见 | GoalConsole.test | ✅ |
| side chat 纠偏 | SideChatPanel.test | ✅ |
| pending_permission 暂停 | GoalConsole.test + test_dogfood_smoke | ✅ |
| checkpoint 创建/加载 | CheckpointPanel.test + test_dogfood_smoke | ✅ |
| 刷新后发现未完成任务 | dogfood + App.test | ✅ |
| 不自动继续 | dogfood + GoalConsole.test | ✅ |

## 失败矩阵覆盖
| 失败路径 | 前端测试 | 后端测试 |
|---|---|---|
| LLM/tool 返回失败 | GoalConsole.test (failed status) | test_agent_loop |
| max_steps 达到 | GoalConsole.test (已停止+已达到最大步数) | test_agent_loop |
| pending_permission | GoalConsole.test + dogfood | test_dogfood_smoke |
| runId 缺失/过期 | App.test (dedup) | test_app (steering 404) |
| checkpoint id 非法 | CheckpointPanel.test (loadAttempted) | test_checkpoint (bad id) |
| workspace 缺失 | App.test (禁用危险动作) | — |

## 安全硬线
- 不自动恢复长任务 ✅
- 不自动审批 pending_permission ✅
- 不自动 rollback checkpoint ✅ (无回滚按钮)
- Side Chat 只 steering ✅ (SideChatPanelApi 只有 steerRun，未知 runId 返回 404)
- Checkpoint 只读摘要 ✅ (无写入/删除/回滚按钮)
- fetcher 注入一致 ✅
- 无 as any / unknown as ✅
- 无 ipcRenderer/shell/process 暴露 ✅
- UI 全中文 ✅

## 测试结果
- vitest: 140 (17 files)
- pytest: 304
- pnpm quality: pass
- desktop build: pass
- lint:chinese-ui: pass

## 文件行数 (≤ 300)
| 文件 | 行数 |
|---|---|
| App.tsx | 196 |
| GoalConsole.tsx | 224 |
| SideChatPanel.tsx | 47 |
| CheckpointPanel.tsx | 56 |
| App.test.tsx | 194 |
| uiWorkflowDogfood.test.tsx | 292 |
| GoalConsole.test.tsx | 259 |
| SideChatPanel.test.tsx | 69 |
| CheckpointPanel.test.tsx | 90 |
| test_dogfood_smoke.py | 235 |

## 新增文件
- docs/exec-plans/active/041-end-to-end-dogfood-reliability.md (49 行)
- docs/decisions/041-end-to-end-dogfood-reliability.md (14 行)
- docs/phase-41-review-gate.md (本文件)
- docs/release/dogfood-smoke.md (69 行)

## 修改文件
- apps/desktop/src/SideChatPanel.test.tsx (+beforeEach +steering不执行工具测试)
- apps/desktop/src/CheckpointPanel.test.tsx (+无回滚按钮测试)
- apps/desktop/src/GoalConsole.test.tsx (+max_steps不显示运行中测试)
- services/agent-core/tests/test_dogfood_smoke.py (+3个可靠性测试)
- scripts/check-docs.mjs (+M41文档路径)
