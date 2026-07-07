# M75 User Preference Memory — 设计决策

## 决策背景
爸爸在长期协作中表达了明确偏好：全中文、称呼爸爸、不自动 push/release、不绕过 PermissionGate 等。这些偏好散落在 project-state 硬规则和各 milestone 执行指令中。M75 将偏好固化到结构化记忆层，确保新窗口接手时也能理解。

## 决策 1：内置硬偏好，从 project-state 提取
**选择**：12 条硬偏好（hard preferences）从 project-state.md 长期硬规则和用户明确指令中固化。

**理由**：
- 偏好来源必须是"明确表达过的长期偏好"，不能从临时上下文推断
- project-state 是唯一经过复审的权威文档
- 内置偏好确保新窗口能立即读取，无需手动配置

## 决策 2：安全偏好不可覆盖
**选择**：category="safety" 的偏好 can_apply_automatically=True，requires_confirmation=False。

**理由**：
- 文档明确："不允许偏好覆盖安全硬规则"
- 安全偏好（不自动 push、不绕过 PermissionGate）必须无条件生效
- 冲突检查 API 验证逻辑一致性

## 决策 3：Secret 检测器
**选择**：`is_secret_attempt()` 检测 token/key/cert/private key 模式。

**理由**：
- "记忆系统不得保存 secret/token/cert/private key"
- 写入前检测比事后扫描更可靠
- 正则检测 sk-、AKIA、PEM header、token assignment 等常见模式

## 风险
- 偏好数量有限（当前 12 条），新增偏好需要修改代码（不是运行时动态写入）
- 偏好冲突检查目前较简单，只检测 auto_apply × requires_confirmation 矛盾
