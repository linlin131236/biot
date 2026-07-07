# M78 Memory Permission Boundary — 设计决策

## 决策背景
M71-M77 建立了多层记忆系统，但缺乏统一的权限边界来区分哪些记忆可以自动读取、哪些需要确认、哪些禁止保存。M78 建立 7 层权限分类，确保 memory 系统的安全边界清晰可审计。

## 决策 1：7 层权限分级
**选择**：public_project → project_internal → user_preference → sensitive → secret → execution_evidence → unknown。

**理由**：
- 文档明确 7 层："public_project、project_internal、user_preference、sensitive、secret、execution_evidence、unknown"
- 每层独立定义 read/write/display 权限
- unknown 默认保守阻断

## 决策 2：Secret 检测 10 种模式
**选择**：正则检测 OpenAI/Anthropic/AWS/GitHub/Slack/JWT 等常见 secret 格式。

**理由**：
- "记忆系统不得保存 secret/token/cert/private key"
- 写入前检测比事后扫描更可靠
- 覆盖主流 API 密钥格式

## 决策 3：敏感内容脱敏而非阻断
**选择**：sensitive 层内容脱敏后仍可返回脱敏版本，secret 层直接阻断。

**理由**：
- 密码、邮箱、电话等敏感信息仍需诊断和调试
- 脱敏版本（如 `[密码：已脱敏]`）保留上下文但不泄露实际值
- secret（token/key/cert）完全阻断，不保留任何形式

## 决策 4：user_preference 写入需要 source_refs
**选择**：`should_block_memory_write` 对 user_preference 内容要求非空 source。

**理由**：
- 文档明确："user_preference：写入需明确来源"
- 防止 Agent 从一次性对话推断偏好并自动写入
- 每条偏好可追溯到文档来源

## 风险
- 正则检测可能漏过非标准 secret 格式
- 敏感内容检测的边界可能不精确（如邮箱正则可能误匹配非邮箱文本）
