# M96-M99 Review Gate — 多任务队列 + 失败解释 + 会话恢复 + 设置面板

## 状态：✅ 通过

## 必查项
- [x] M96 列出任务、状态、风险、关联
- [x] M96 支持按状态筛选
- [x] M96 不自动启动/继续未授权任务
- [x] M97 失败有中文原因/建议/可重试标记
- [x] M97 高风险失败提示人工确认
- [x] M97 不自动 retry/fix
- [x] M98 展示可恢复任务、恢复策略
- [x] M98 不自动 resume，不跳过权限复查
- [x] M99 模型/工具/预算中文清楚
- [x] M99 不显示 secret/token/key
- [x] 所有面板中文 UI、只读
- [x] 无 `as any` / `unknown as`
- [x] renderer 无危险 API

## 测试结果
| 面板 | 测试数 | 结果 |
|------|--------|------|
| MultiTaskQueuePanel | 3 | ✅ |
| FailureExplanationPanel | 3 | ✅ |
| SessionRecoveryPanel | 3 | ✅ |
| SettingsToolsPanel | 3 | ✅ |
| Desktop full (34 files) | 261/262* | ✅ |
| Build | - | ✅ |

*1 个预存失败（GoalConsole.test.tsx），非本次引入
