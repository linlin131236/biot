# M37 Review Gate — Desktop Goal Console

## Changed Files

| File | Lines | Change |
|------|-------|--------|
| `apps/desktop/src/GoalConsole.tsx` | 102 | **新增** 长任务驾驶舱组件 |
| `apps/desktop/src/GoalConsole.test.tsx` | 121 | **新增** 13 个 M37 测试 |
| `apps/desktop/src/App.tsx` | 185 | 接入 GoalConsole + harnessClientAutonomy import |
| `apps/desktop/src/harnessClientAutonomy.ts` | 97 | 补 clearGoal/fetchGoalEvidence/fetchGoalBudget |
| `apps/desktop/src/harnessClientAutonomy.test.ts` | 83 | 补 3 个新方法测试 |
| `docs/exec-plans/active/037-desktop-goal-console.md` | 19 | **新增** |
| `docs/decisions/037-desktop-goal-console.md` | 21 | **新增** |
| `scripts/check-docs.mjs` | 2 | 补 M37 文档 |

## NOT Changed (Safety Boundaries Intact)

- ❌ No changes to `services/agent-core/` — backend untouched
- ❌ No changes to `packages/shared/src/protocol-autonomy.ts` — types reused
- ❌ No changes to `electron/preload.ts` — no new IPC channels
- ❌ No changes to `electron/main.ts` — no new Electron exposure
- ❌ No changes to permission/approval/verification logic
- ❌ No changes to tool executor or shell access

## Test Results

- **299 pytest** ✅
- **105 vitest** ✅ (15 files, including 13 new GoalConsole + 3 new harnessClientAutonomy)
- **11 shared vitest** ✅
- **pnpm quality** ✅ (size/docs/boundaries/architecture/release/runtime/chinese-ui)
- **desktop build** ✅

## Chinese UI Check

- `pnpm lint:chinese-ui` ✅ — zero mojibake, zero tool protocol violations
- GoalConsole all Chinese labels: 长任务驾驶舱/长任务目标/开始长任务/暂停任务/恢复任务/停止任务/运行中/已暂停/等待人工批准/已停止/已完成/失败/未开始/已达到最大步数

## Security Check

- `ipcRenderer` only in `preload.ts` (M36, unchanged)
- renderer `src/` has no ipcRenderer/contextBridge/shell/process/fs
- GoalConsole.tsx comment: "不直接访问 fs/shell/process/ipcRenderer"
- Test assertion: GoalConsole HTML does not contain ipcRenderer/shell/process
- No new Electron IPC channels
- No auto-approve for pending_permission — GoalConsole shows "等待人工批准"
- max_steps reached → "已达到最大步数" + stopped state
- No workspace → "开始长任务" button disabled

## Known Risks

1. GoalConsole `goal` prop currently receives `goalInfo as any` from App.tsx — should refine type when App state gains proper Goal tracking
2. `handleStart` creates goal with hardcoded `max_steps: 10` and `criteria: ['任务完成']` — UI should expose these as configurable inputs in follow-up
3. GoalConsole does not auto-refresh goal status — needs polling or WebSocket in production

## Reviewer Focus Tomorrow

1. GoalConsole UX: is "长任务目标" label distinct enough from toolbar "任务目标"?
2. Goal state flow: verify the create→running→paused→stopped lifecycle works end-to-end with real backend
3. Evidence display: `fetchGoalEvidence` returns raw array — needs UI formatting in next milestone
