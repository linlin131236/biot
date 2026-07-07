# M96 Exec Plan - 多任务队列

## 目标
展示当前多任务队列的中文概览，帮助爸爸看到哪些任务在等待、阻断、完成或需要人工处理。

## 参考资料
- ZCode看板法：任务队列要可扫描、可排序、可定位。
- Agent产品化流水线：队列页不能自己启动任务。

## 实施
- 新增 `MultiTaskQueuePanel.tsx` 和测试。
- 新增 `multi_task_queue_api.py` 聚合目标、闭环和 planner 状态。
- 路由只读，不提供 start/resume/approve。

## 验收
- 显示中文状态和任务摘要。
- 不自动启动、继续、重试任务。
- renderer 安全扫描干净。
