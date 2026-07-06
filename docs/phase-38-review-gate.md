# Phase 38 Review Gate

## M38 实现摘要
M38 在 M37 长任务驾驶舱基础上增加了长任务可观测性与恢复能力。桌面重启后能发现未完成长任务，默认不自动继续执行，用户点击"恢复任务"才调用 resumeGoal。时间线和证据由 GoalConsole 内部 useEffect 主动 fetch（不依赖外部 props 传入）。

## 改动文件
- `apps/desktop/src/GoalConsole.tsx` (220行) — unfinishedGoals prop，发现未完成长任务 banner，handleResumeFromBanner（resumeGoal返回检查+startRun+runAgentLoop），handleResume（resumeGoal返回检查），nextSuggestion，loopStatusToGoalStatus 支持 failed/max_steps 诊断，useEffect 主动 fetch timeline/evidence
- `apps/desktop/src/GoalConsole.test.tsx` (245行) — 22 测试覆盖 M37+M38 全部行为（含 resumeGoal 返回 paused 阻断测试）
- `apps/desktop/src/App.tsx` — fetchUnfinishedGoals useEffect，unfinishedGoals state 传给 GoalConsole，移除 as any
- `apps/desktop/src/uiWorkflowDogfood.test.tsx` — M38 App 级测试（fetch unfinished、不自动 runAgentLoop、等待人工批准）
- `apps/desktop/src/harnessClientAutonomy.ts` — fetchRunTimeline 返回 TimelineEvent[]，fetchGoalEvidence 返回 GoalEvidence[]
- `apps/desktop/src/harnessClientAutonomy.test.ts` — fetchUnfinishedGoals+fetchRunTimeline+fetchGoalEvidence client 测试
- `packages/shared/src/protocol-autonomy.ts` — TimelineEvent、GoalEvidence 类型
- `packages/shared/src/protocol-autonomy.test.ts` — 类型可构造性测试
- `docs/exec-plans/active/038-goal-timeline-resume.md` — M38 计划文档
- `docs/decisions/038-goal-timeline-resume.md` — M38 决策文档
- `docs/phase-38-review-gate.md` — 本文件
- `scripts/check-docs.mjs` — 增加 038 文档条目

## 恢复许可检查
resumeGoal 返回后，必须检查 `g.status === 'running'` 才允许继续 startRun/runAgentLoop。
- 返回 `paused`（后端文件冲突保护）→ 阻断恢复，显示"恢复被阻止，请检查工作区冲突"
- 冷启动恢复和普通恢复两条路径均有此检查

## 不自动恢复说明
桌面重启后发现未完成长任务，默认不自动继续执行。用户必须点击"恢复任务"按钮才调用 resumeGoal。resumeGoal 返回 running 后，冷启动路径调 startRun 获取新 runId 再跑 runAgentLoop；普通恢复路径在已有 runId 时跑 runAgentLoop。

## pending_permission 行为
- loop 返回 pending_permission → 状态显示"已暂停"，诊断显示"等待人工批准"
- 不自动批准，不绕过 permission gate

## max_steps 行为
- loop 返回 steps === maxSteps → 状态显示"已停止"，诊断显示"已达到最大步数"

## failed 行为
- loop 返回 failed → 状态显示"失败"，诊断显示"失败"+ error 信息
- nextSuggestion: "建议：检查错误日志后重新创建任务"

## 安全边界
- renderer 不出现 ipcRenderer/fs/shell/process（测试验证）
- 不新增危险工具能力
- 不绕过 permission gate
- resumeGoal 返回非 running 时阻断后续执行
- 所有新增 UI 文案中文（lint:chinese-ui 通过）

## 时间线和证据
- timeline/evidence 由 GoalConsole 内部 useEffect 主动 fetch，不依赖外部 props
- evidence：依赖 currentGoal/goal/unfinishedGoals，有目标即 fetch
- timeline：依赖 currentRunId，有 runId 才 fetch
- 内嵌面板，不拆分独立组件（GoalConsole 220行在 300行限制内）

## 测试结果
- 299 pytest 全绿
- 120 vitest 全绿（含 22 GoalConsole + 21 dogfood + 10 App + 9 autonomy）
- pnpm quality 通过
- desktop build 通过

## Reviewer 重点
1. 验证桌面端实际渲染：是否能看到"发现未完成长任务"banner
2. 验证恢复流程：resumeGoal 返回 paused 时是否阻断 startRun/runAgentLoop
3. 验证时间线/证据面板在真实数据下的展示效果
4. 检查 GoalConsole 220 行是否接近拆分阈值
5. 检查 App.tsx 行数是否还有余量接 Phase 39

## 本地 Commits（M38）
1. `docs: plan goal timeline resume`
2. `feat: add goal resume timeline client`
3. `feat: add goal resume diagnostics`
4. `feat: wire goal resume into desktop app`
5. `feat: show goal timeline evidence`
6. `test: harden goal resume safety gates`
7. `docs: add M38 review gate`
8. `fix: resume cold-start runs agent loop, evidence fetched by useEffect, remove as any`
9. `fix: check resumeGoal return status before continuing agent loop`
10. `docs: sync review gate with implementation, type fetchGoalEvidence as GoalEvidence[]`
