# Beta Privacy Security Audit

## 覆盖范围
- prompt injection：检查工具输出和用户输入不能直接变成高权限指令。
- permission：所有副作用工具必须经过 PermissionGate 或人工批准边界。
- secret：token、key、cert、private key 必须脱敏，不能进入记忆或审计明文。
- supply chain：MCP、工具、插件和外部资料只能作为不可信输入处理。
- privacy：用户偏好、项目记忆和执行证据必须最小化暴露。
- readonly audit：审计信号只读，不自动执行、不自动批准。

## 当前结论
M124 只做隐私安全审计，不替代 PermissionGate。
