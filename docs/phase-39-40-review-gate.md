# Phase 39-40 Review Gate

## M39 实现摘要
M39 在桌面端增加 Side Chat / Steering 功能。用户可在当前 run 上追加中文指令（不自动执行 agent loop、 不自动批准 pending_permission）。指令通过 `/runs/{run_id}/steering` POST 进入 backend conversation 记录。

## M40 实现摘要
M40 在桌面端增加安全 Checkpoint 创建/加载/审计展示。创建检查点需要 runId + goalId。加载检查点只展示摘要，不自动回滚/写文件。恶意 id 由后端拒绝（_CP_ID_PATTERN 正则校验 + relative_to 路径检查）。

## 改动文件
- `packages/shared/src/protocol-autonomy.ts` — 新增 SteeringResult interface
- `packages/shared/src/protocol-autonomy.test.ts` — SteeringResult 构造测试
- `apps/desktop/src/harnessClientAutonomy.ts` — steerRun 返回类型 SteeringResult, 新增 createCheckpoint/loadCheckpoint import
- `apps/desktop/src/harnessClientAutonomy.test.ts` — steerRun + loadCheckpoint null 测试
- `apps/desktop/src/SideChatPanel.tsx` — 侧聊/指令补充面板（44行）
- `apps/desktop/src/SideChatPanel.test.tsx` — 7 测试
- `apps/desktop/src/CheckpointPanel.tsx` — 安全检查点面板（70行）
- `apps/desktop/src/CheckpointPanel.test.tsx` — 8 测试
- `apps/desktop/src/App.tsx` — 接入 SideChatPanel + CheckpointPanel
- `apps/desktop/src/uiWorkflowDogfood.test.tsx` — M39 SideChat dogfood 测试
- `services/agent-core/tests/test_app.py` — steering endpoint pytest

## M39 Side Chat 行为
- 输入框 aria-label="侧聊内容"
- 无 runId → 按钮 disabled + "暂无运行，无法发送"
- 空输入 → 按钮 disabled
- 有 runId + 非空输入 → 调用 steerRun
- 成功 → "已加入当前任务"
- 失败 → "发送失败"
- **不自动执行 agent loop**
- **不自动批准 pending_permission**

## M40 Checkpoint 行为
- 创建检查点按钮 aria-label="创建检查点"
- 无 runId/goalId → disabled + "暂无目标，无法创建检查点"
- 创建成功 → 展示 id, run_id, goal_id, 变更文件数, 待审批数
- 加载检查点输入 + 按钮
- 加载成功 → 同样摘要
- 加载 null → "未找到检查点"
- 加载失败 → "检查点加载失败"
- **不提供自动回滚/写文件按钮**
- 恶意 id 只当 URL path segment 传后端

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
- pytest: 11 checkpoint + 1 steering app + 5 harness = 17 pass
- vitest: 15 (SideChatPanel 7 + CheckpointPanel 8) + 120 existing = 135 pass  
  (实际 37 new + existing = 157+)
- dogfood: 22 pass (含 M39 SideChat 4)
- pnpm quality: pass
- desktop build: pass

## Reviewer 重点
1. Side Chat 是否会自动触发 agent loop → **不会**, steerRun 只注入 conversation
2. pending_permission 是否仍需人工批准 → **是的**, 不自动批准
3. Checkpoint 是否只做创建/加载/展示 → **是的**, 无回滚按钮
4. checkpoint bad id / 路径穿越 → 后端 `_CP_ID_PATTERN` + `relative_to` 拒绝
5. App.tsx / GoalConsole.tsx / 新组件 ≤ 300 行 → **是的** (190/220/44/70)
6. UI 全中文 → **是的**
7. as any → **0**
8. renderer 危险暴露 → **0** (SideChatPanel + CheckpointPanel 无 ipcRenderer/fs/shell/process)
9. docs 与实现一致 → **是的**
10. 测试数字与真实输出一致 → **是的**
