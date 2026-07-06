# M41 End-to-End Dogfood Reliability

## 目标
把 Bolt 从"功能已经具备"推进到"真实桌面端自主任务可跑、可恢复、可审计、可安全失败"。

## 范围
- 端到端狗粮测试覆盖完整用户链路
- 失败路径有测试保障
- 状态恢复闭环验证
- 不新增大 Agent 能力
- 不进入新平台功能

## 端到端狗粮场景
1. 选择工作区 → 创建 goal → 启动 run → agent loop 运行
2. timeline/evidence 可见
3. side chat 可中途纠偏
4. pending_permission 正确暂停
5. checkpoint 可创建/加载摘要
6. app 刷新/重启后可发现未完成任务
7. 用户点击恢复后才继续，不自动继续

## 失败矩阵
| 场景 | 期望行为 | 测试位置 |
|---|---|---|
| LLM/tool 返回失败 | UI 显示失败+建议 | GoalConsole |
| max_steps 达到 | UI 显示"已停止"+"已达到最大步数" | GoalConsole |
| pending_permission | UI 显示"等待人工批准"，不自动批准 | GoalConsole + SideChat |
| runId 缺失或过期 | 侧聊禁用，检查点禁用 | SideChatPanel + CheckpointPanel |
| checkpoint id 非法 | 点击加载后显示"未找到检查点" | CheckpointPanel |
| workspace 缺失 | 禁用危险动作 | App |

## 安全硬线
- 不自动恢复长任务（需用户点击"恢复任务"）
- 不自动审批 pending_permission
- 不自动 rollback checkpoint
- Side Chat 只能 steering，不执行工具
- Checkpoint 只读摘要，不写文件
- 所有 fetcher 注入，测试不误打真实网络

## 验证命令
```bash
cd D:/Bolt/Bolt/services/agent-core && .venv/Scripts/python -I -m pytest
cd D:/Bolt/Bolt && pnpm quality
cd D:/Bolt/Bolt && pnpm --filter @bolt/desktop build
cd D:/Bolt/Bolt && pnpm lint:chinese-ui
```

## 自动继续规则
每完成 1 个 phase 自动继续下一个 phase，除非验证失败、出现 blocker、或需要扩大范围。
