# Phase 39-40 Review Gate

## M39 实现摘要
M39 在桌面端增加 Side Chat / Steering 功能。用户可在当前 run 上追加中文指令（不自动执行 agent loop、 不自动批准 pending_permission）。指令通过 `/runs/{run_id}/steering` POST 进入 backend conversation 记录。本地消息列表显示已发送记录和状态。

## M40 实现摘要
M40 在桌面端增加安全 Checkpoint 创建/加载/审计展示。创建检查点需要 runId + goalId（通过 GoalConsole onGoalChange 回传）。加载检查点只展示摘要，不自动回滚/写文件。loadAttempted 防止提前显示"未找到"。恶意 id 由后端拒绝。

## 改动文件
- `packages/shared/src/protocol-autonomy.ts` — 新增 SteeringResult interface
- `packages/shared/src/protocol-autonomy.test.ts` — SteeringResult 构造测试
- `apps/desktop/src/harnessClientAutonomy.ts` — steerRun 返回类型 SteeringResult
- `apps/desktop/src/harnessClientAutonomy.test.ts` — steerRun + loadCheckpoint null 测试
- `apps/desktop/src/SideChatPanel.tsx` — 侧聊/指令补充面板（47行），含本地消息列表
- `apps/desktop/src/SideChatPanel.test.tsx` — 8 测试
- `apps/desktop/src/CheckpointPanel.tsx` — 安全检查点面板（56行），含 loadAttempted
- `apps/desktop/src/CheckpointPanel.test.tsx` — 9 测试
- `apps/desktop/src/GoalConsole.tsx` — 新增 onGoalChange callback（224行）
- `apps/desktop/src/App.tsx` — 接入 SideChatPanel + CheckpointPanel + handleGoalConsoleChange（195行）
- `services/agent-core/tests/test_app.py` — steering endpoint pytest
- `docs/phase-39-40-review-gate.md` — review gate 文档

## M39 Side Chat 行为
- 输入框 aria-label="侧聊内容"
- 无 runId → 按钮 disabled + "暂无运行，无法发送"
- 空输入 → 按钮 disabled
- 有 runId + 非空输入 → 调用 steerRun
- 成功 → 消息出现在聊天记录列表（status: sent）
- 失败 → 消息出现在聊天记录列表（status: error）+ "发送失败"
- 支持 Enter 键发送
- **不自动执行 agent loop**
- **不自动批准 pending_permission**

## M40 Checkpoint 行为
- 创建检查点按钮 aria-label="创建检查点"
- 无 runId/goalId → disabled + "暂无目标，无法创建检查点"
- GoalConsole 创建/恢复 goal 后通过 onGoalChange 回传 goalId + runId 给 App
- 创建成功 → 展示 id, run_id, goal_id, 变更文件数, 待审批数
- 加载检查点输入 + 按钮
- 输入 ID 但未点击加载 → 不显示"未找到检查点"
- 点击加载后 null → "未找到检查点"
- 加载成功 → 同样摘要
- 加载失败 → "检查点加载失败"
- **不提供自动回滚/写文件按钮**

## 不自动执行说明
- Side Chat 发送 steering 不触发 `/agent-loops`
- pending_permission 仍需人工批准
- Checkpoint 不自动回滚/写文件

## 安全边界
- Side Chat 是 steering/context 补充，不是 permission bypass
- Checkpoint 是审计/恢复前置，不是自动回滚
- 后端 checkpoint: `_CP_ID_PATTERN` 校验 + `relative_to` 路径检查
- 恶意 id: `../../../etc/passwd` → 后端返回 null
- 渲染器不暴露 ipcRenderer/fs/shell/process

## 测试结果
- pytest: 300 passed
- vitest: 138 passed (17 files)
- shared: 18 passed (2 files)
- pnpm quality: passed (lint:size + lint:docs + lint:boundaries + lint:architecture + lint:release + lint:package-runtime + lint:chinese-ui + test)
- desktop build: passed

## Reviewer 重点
1. Side Chat 是否会自动触发 agent loop → **不会**, steerRun 只注入 conversation
2. pending_permission 是否仍需人工批准 → **是的**, 不自动批准
3. Checkpoint 是否只做创建/加载/展示 → **是的**, 无回滚按钮
4. GoalConsole goal 是否回传给 CheckpointPanel → **是的**, onGoalChange callback
5. Side Chat 是否有消息记录 → **是的**, 本地 ChatEntry 列表
6. Checkpoint 输入 ID 时是否提前显示未找到 → **不会**, loadAttempted 控制
7. checkpoint bad id / 路径穿越 → 后端 `_CP_ID_PATTERN` + `relative_to` 拒绝
8. 所有源码文件 ≤ 300 行 → **是的** (SideChat 47, Checkpoint 56, GoalConsole 224, App 195)
9. UI 全中文 → **是的**
10. as any → **0**
11. renderer 危险暴露 → **0**
