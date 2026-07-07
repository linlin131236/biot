# M99 Exec Plan - 设置/模型/工具面板

## 目标
把模型、预算、工具策略做成中文只读设置页，让爸爸知道当前系统怎么配置，但不在这里修改 secret 或执行工具。

## 参考资料
- Agent产品化流水线：设置页默认只读，敏感配置不落 UI。
- 桌面AI编程Agent全流程架构对比：工具策略必须显式显示 PermissionGate 边界。

## 实施
- 新增 `SettingsToolsPanel.tsx` 和测试。
- 新增 `settings_tools_api.py`，返回模型状态、预算摘要和工具策略。
- 不显示 secret/token/key 明文，不提供执行入口。

## 验收
- 中文展示模型、预算、工具策略。
- 测试确认不渲染 secret/token/key。
- renderer 安全扫描干净。
