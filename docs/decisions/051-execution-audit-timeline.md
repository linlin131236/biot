# Decision 051: Execution Audit Timeline

## 决策
新增只读 execution audit timeline 聚合层，用已有 queue、handoff、closure evidence 状态生成中文审计摘要。

## 原因
M48-M50 已经把 queue、handoff、PermissionGate result ingestion 和 closure evidence 串起来，但用户缺少一个只读视图理解某个 closure 的闭环进度。该能力应是审计聚合，不应成为新的执行入口。

## 约束
- 不新增 approve/reject/request-permission 能力。
- 不自动执行命令，不启动 Agent Loop，不创建 goal。
- 不绕过 PermissionGate，不自动批准 PermissionGate。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 所有 UI 文案中文。

## 方案
- 后端新增 `execution_audit_timeline.py`，从 queue、handoff、closure 读取状态并输出排序事件。
- 后端新增 GET API：`/task-closures/{closure_id}/execution-audit-timeline`。
- shared 增加 `ExecutionAuditTimelineEvent` 类型。
- desktop client 增加 `fetchExecutionAuditTimeline`。
- `ExecutionHandoffPanel` 附近展示只读时间线，不添加任何执行按钮。
