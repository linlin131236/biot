# M126 Review Gate - Real Agent Workbench

## 结论

M126 完成：只读 Agent 工作台已接入桌面第一屏。

## 检查项

- `/product-workbench` 已注册。
- `ProductWorkbenchPanel.tsx` 已接入 `PanelsSection`。
- 8 个阶段完整：用户意图、计划拆解、读取上下文、补丁预览、人工批准、应用补丁、测试验证、审计与恢复。
- 安全边界明确：不自动 apply、不自动 approve、写入必须爸爸批准。
- targeted backend tests 通过。
- targeted desktop tests 通过。
- 未 push / 未 release / 未 tag / 未 delete。
- 未进入 M127。

## 放行条件

- M126 targeted tests 全绿。
- 文档链完整。
- project-state 更新为 M126 本地完成。

