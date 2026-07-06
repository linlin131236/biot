# Phase 38 Review Gate

## M38 实现摘要
M38 在 M37 长任务驾驶舱基础上增加了长任务可观测性与恢复能力。桌面重启后能发现未完成长任务，默认不自动继续执行，用户点击"恢复任务"才调用 resumeGoal。时间线和证据可视化显示在 GoalConsole goalDetails 区域。

## 改动文件
- `apps/desktop/src/GoalConsole.tsx` — 增加 unfinishedGoals/timeline/evidence props，发现未完成长任务 banner，resumeFromBanner，nextSuggestion，loopStatusToGoalStatus 支持 failed/max_steps 诊断
- `apps/desktop/src/GoalConsole.test.tsx` — 精简到 209 行，19 测试覆盖 M37+M38 全部行为
- `apps/desktop/src/App.tsx` — 增加 fetchUnfinishedGoals useEffect，fetchRunTimeline api prop，unfinishedGoals state 传给 GoalConsole
- `apps/desktop/src/uiWorkflowDogfood.test.tsx` — 增加 3 个 M38 App 级测试（fetch unfinished、不自动 runAgentLoop、等待人工批准）
- `apps/desktop/src/harnessClientAutonomy.ts` — fetchRunTimeline 返回 TimelineEvent[] 类型
- `apps/desktop/src/harnessClientAutonomy.test.ts` — 增加 fetchUnfinishedGoals+fetchRunTimeline client 测试
- `packages/shared/src/protocol-autonomy.ts` — 增加 TimelineEvent、GoalEvidence 类型
- `packages/shared/src/protocol-autonomy.test.ts` — 新增类型可构造性测试
- `docs/exec-plans/active/038-goal-timeline-resume.md` — M38 计划文档
- `docs/decisions/038-goal-timeline-resume.md` — M38 决策文档
- `docs/phase-38-review-gate.md` — 本文件
- `scripts/check-docs.mjs` — 增加 038 文档条目

## 不自动恢复说明
桌面重启后发现未完成长任务，默认不自动继续执行。用户必须点击"恢复任务"按钮才调用 resumeGoal。runAgentLoop 不在恢复流程中自动调用（需要先有 runId）。

## pending_permission 行为
- loop 返回 pending_permission → 状态显示"已暂停"，诊断显示"等待人工批准"
- 不自动批准，不绕过 permission gate
- 用户在 PermissionsPanel 手动批准后才能继续

## max_steps 行为
- loop 返回 steps === maxSteps → 状态显示"已停止"，诊断显示"已达到最大步数"
- 建议文案：已达到最大步数限制

## failed 行为
- loop 返回 failed → 状态显示"失败"，诊断显示"失败"+ error 信息
- 建议：检查错误日志后重新创建任务

## 安全边界
- renderer 不出现 ipcRenderer/fs/shell/process（测试验证）
- 不新增危险工具能力
- 不绕过 permission gate
- 不自动批准 pending_permission
- 所有新增 UI 文案中文（lint:chinese-ui 通过）

## 测试结果
- 299 pytest 全绿
- 117 vitest 全绿（含 19 GoalConsole + 21 dogfood + 10 App 等）
- pnpm quality 通过
- desktop build 通过
- lint:chinese-ui 通过
- lint:architecture 通过
- lint:boundaries 通过

## Reviewer 明天重点
1. 验证桌面端实际渲染：是否能看到"发现未完成长任务"banner
2. 验证恢复流程：点击"恢复任务"后 resumeGoal 是否被正确调用
3. 验证时间线/证据面板在真实数据下的展示效果
4. 检查 GoalConsole 194 行是否接近拆分阈值
5. 检查 App.tsx 188 行是否还有余量接 Phase 39

## 本地 Commits（M38）
1. `docs: plan goal timeline resume`
2. `feat: add goal resume timeline client`
3. `feat: add goal resume diagnostics`
4. `feat: wire goal resume into desktop app`
5. `feat: show goal timeline evidence`
6. `test: harden goal resume safety gates`
