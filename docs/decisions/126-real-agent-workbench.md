# M126 Decision - Real Agent Workbench

## 决策

采用“只读聚合工作台”，不在 M126 里重写 App 架构，也不新增写入动作。

## 理由

- 现有能力已经分散存在：任务首页、补丁预览、批准 apply、测试、失败解释和恢复面板都有基础。
- 当前最大问题不是缺功能，而是爸爸很难一眼看懂“一句话任务如何走到补丁、批准、测试和恢复”。
- 只读聚合可以降低安全风险，不绕过 PermissionGate。

## 安全边界

- 不自动 apply。
- 不自动 approve。
- 不自动运行测试。
- 不执行 push/release/tag/delete。
- renderer 不访问 `ipcRenderer` / `fs` / `shell` / `process`。

