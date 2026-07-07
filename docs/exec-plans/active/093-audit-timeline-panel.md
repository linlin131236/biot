# M93 Exec Plan - 审计时间线视图

## 目标
把执行审计时间线做成桌面只读中文面板，让爸爸能按任务查看关键事件、状态、证据摘要和异常提示。

## 参考资料
- Agent产品化流水线：界面必须服务验收，不替用户做隐式执行。
- ZCode看板法：状态、证据、下一步要能一眼扫到。
- 桌面AI编程Agent全流程架构对比：Tool Result 必须回写 Trace Record。

## 实施
- 新增 `AuditTimelinePanel.tsx` 和测试。
- 新增 `audit_timeline_api.py` 聚合已有审计时间线能力。
- 在 `app.py` 注册只读路由。
- 不新增写入、批准、执行、恢复入口。

## 验收
- 面板全中文。
- 空状态、加载、错误、事件列表均有测试。
- renderer 不访问 fs/shell/process/ipcRenderer。
- 不绕过 PermissionGate。
