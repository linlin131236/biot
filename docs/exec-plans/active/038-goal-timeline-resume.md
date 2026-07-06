# M38 Goal Timeline + Resume

## 目标
在 M37 长任务驾驶舱基础上，把 Bolt 推进到"长任务可观察、可恢复、可诊断"的状态。

## 范围
- 桌面端发现未完成长任务
- 时间线事件可视化
- 证据记录可视化
- pending_permission / max_steps / failed 中文诊断提示
- 不自动恢复，点击恢复才继续

## 不做的事
- 不新增危险 Agent 工具能力
- 不绕过 permission gate
- 不自动批准 pending_permission
- 不改 planner / agent loop / tool executor 核心语义
- 不进入 M39

## 实现计划

### Phase 0: 只读体检 ✅
- 确认 fetchUnfinishedGoals / fetchGoalEvidence / fetchRunTimeline / runAgentLoop 已有
- 确认 GoalConsole.tsx 154行、App.tsx 186行、后端路由齐全

### Phase 1: 文档
- exec-plan / decision / review-gate 骨架

### Phase 2: 失败测试
- 桌面恢复发现、unfinished goal 展示、不自动继续、点击恢复才执行
- pending_permission/max_steps/failed 中文诊断
- 时间线空/有事件、evidence 空/有记录

### Phase 3: client 方法和类型
- 补齐 fetchUnfinishedGoals 测试
- 确认 fetchRunTimeline 类型

### Phase 4: GoalConsole 恢复能力
- 支持 unfinishedGoals 传入
- 恢复按钮逻辑
- 状态诊断文案

### Phase 5: App 接线
- App 启动调 fetchUnfinishedGoals
- 传给 GoalConsole

### Phase 6: 时间线和证据面板
- GoalTimelinePanel / GoalEvidencePanel 拆分

### Phase 7: 安全与中文质量门

### Phase 8: 全量验证

### Phase 9: 更新审查报告

### Phase 10: 最终收口

## 关键约束
- 所有 UI 文案中文
- 不自动恢复执行
- pending_permission 不自动批准
- 每个源文件 ≤ 300 行
- 先写测试再实现
