# M40 Safe Checkpoints

## 目标
桌面端支持安全 Checkpoint 创建/加载/审计展示。

## 范围
- 新增 CheckpointPanel 组件
- 创建检查点（需要 runId + goalId）
- 加载检查点（输入 id，展示摘要）
- 审计展示：id, run_id, goal_id, changed_files 数量, pending_permissions 数量
- 不自动回滚/写文件
- 所有 UI 中文

## 不做的事
- 不提供"自动回滚/立即恢复写文件"按钮
- 不绕过 checkpoint 安全校验（bad id / 路径穿越由后端拒绝）
- 不进入 M41
- M40 只做审计预览，不做自动回滚

## 实现计划

### Phase 5: CheckpointPanel.tsx + test
- 创建/加载 UI
- 审计摘要展示
- null/错误处理

### Phase 6: App 接线
- 传 runId + goalInfo?.id
- dogfood 测试

### Phase 7: 后端安全测试补强
- 确认 bad id / 路径穿越已有覆盖

## 关键约束
- Checkpoint 是审计/恢复前置，不是自动回滚
- 加载只展示摘要，不写文件
- 后端已有 _CP_ID_PATTERN 校验
- 恶意 id 只当 URL path segment 传后端
- 每个文件 ≤ 300 行
