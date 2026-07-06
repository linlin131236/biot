# M39 Side Chat Steering

## 目标
桌面端支持长任务 Side Chat / Steering：用户可在当前 run 上追加中文指令，指令进入 backend conversation 记录。

## 范围
- 新增 SideChatPanel 组件
- 有 runId 时可发送 steering 消息
- 无 runId 时禁用发送
- 空输入禁用发送
- 不自动执行 agent loop
- 不自动批准 pending_permission
- 所有 UI 中文

## 不做的事
- 不新增危险 Agent 工具能力
- 不绕过 permission gate
- 不自动批准 pending_permission
- 不自动跑 agent loop
- 不进入 M41

## 实现计划

### Phase 2: 类型 + client 测试
- SteeringResult interface (status: string)
- harnessClientAutonomy.test.ts 补 steerRun/createCheckpoint/loadCheckpoint 测试

### Phase 3: SideChatPanel.tsx + test
- 输入框 + 发送按钮 + 状态提示
- 无 runId 禁用
- 成功/失败中文提示

### Phase 4: App 接线
- 传 runId + steerRun api
- dogfood 测试

## 关键约束
- 所有 UI 文案中文
- 不自动执行
- renderer 无危险暴露
- 每个文件 ≤ 300 行
