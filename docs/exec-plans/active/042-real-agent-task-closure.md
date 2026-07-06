# M42 Real Agent Task Closure

## 目标
把 Bolt 从"端到端狗粮链路可验证"推进到"真实代码/文档任务可以形成闭环"。

## 范围
- 任务模板：bugfix / docs / test / quality / review
- 任务状态机：10 个中文状态
- 结构化闭环证据记录
- 失败修复边界（最多 N 次重试）
- 审查面板

## 不做
- M43
- 发布/Release
- MoA/多 Agent 扩张
- 自动 push
- 自动审批 permission
- 自动删除文件
- 写 workspace 外

## 任务模板
| id | label | description |
|---|---|---|
| bugfix | 修复小问题 | 定位并修复代码缺陷 |
| docs | 更新文档 | 添加或修正文档内容 |
| test | 增加测试 | 为现有代码补充测试 |
| quality | 跑质量门 | 运行 lint/build/test 验证 |
| review | 生成审查摘要 | 汇总变更和验证结果 |

## 任务状态机
pending → planning → executing → waiting_permission → verifying → repairing → reviewing → completed / failed / stopped

合法流转：
- pending → planning
- planning → executing
- executing → waiting_permission / verifying / failed
- waiting_permission → executing（批准后）
- verifying → completed / repairing / failed
- repairing → executing（重试）/ failed（超限）/ stopped
- reviewing → completed / failed
- 任何状态 → stopped（用户停止）

## 失败修复边界
- 最多 3 次修复重试
- 不无限循环
- 失败时保留 evidence/timeline
- 超出边界转为 failed + "需要人工处理"

## Evidence 结构
- objective, template_id, plan_summary
- changed_files, commands, command_results
- permission_request_ids, retry_count
- final_status, review_summary, next_action

## UI 中文要求
- 面板标题：任务闭环
- 模板选择中文 label
- 状态显示中文
- 不出现英文 UI
- 不提供 push/release/delete 按钮

## 验证命令
- pnpm quality
- pnpm --filter @bolt/desktop test
- pnpm --filter @bolt/desktop build
- pnpm lint:chinese-ui
- cd services/agent-core && .venv\Scripts\python -I -m pytest

## 自动继续规则
每完成 1 个 phase 自动继续下一个 phase，除非验证失败、出现 blocker、或需要扩大范围。
