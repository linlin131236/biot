# Bolt 阶段 A：安全受控 Beta 设计规格

- 日期：2026-07-10
- 状态：待用户书面审阅
- 分支：`feat/safe-controlled-beta`
- 产品形态：Electron Desktop + 本机 Python Agent Core

## 1. 目标

阶段 A 将 Bolt 从内部工程候选推进到“可安全受控 Beta”。本阶段关闭两个 P0 安全缺口，建立桌面端与 Agent Core 的单一契约，为官方 OpenAI-compatible 供应商和用户自定义中转站提供安全的桌面配置体验，并以真实 Windows 验收证据而非文档声明作为放行依据。

阶段 A 完成后，用户只需安装并运行 `Bolt.exe`。用户不需要打开浏览器、管理 Python 服务、配置 Agent Core URL 或接触内部 OpenAPI。

## 2. 产品边界

### 2.1 Desktop-only

Bolt 是桌面产品，不提供 Web 管理后台。

- Electron Main Process 启动、监督并关闭 Python Agent Core。
- Agent Core 仅监听 loopback 随机端口。
- Agent Core Token 与 endpoint 由桌面运行时持有，不写入 renderer storage。
- Renderer 不能配置 Core URL，也不能退回普通网络 `fetch` 调用 Core。
- 打包版关闭 Swagger、ReDoc 和在线 OpenAPI 页面。
- OpenAPI 仅在构建时离线导出并生成 TypeScript 内部客户端。

### 2.2 参考图使用原则

用户提供的 Codex/ZCode 图片只用于参考桌面布局、信息密度和交互组织，不决定 Bolt 的功能清单。

- 主工作区采用项目/会话侧栏、任务工作区和底部输入区。
- 设置中心采用固定分类侧栏和右侧配置内容。
- 模型设置采用供应商列表与供应商详情双栏布局。
- 只呈现 Bolt 当前真实拥有且已接入的能力。
- 不复制外部产品的品牌、文案、套餐、宠物、商城或其他 Bolt 未拥有的功能。
- 不制作空按钮、假开关、“即将推出”页面或演示统计。

### 2.3 设置与执行分离

设置中心负责配置、默认值、状态、健康检查、数据管理和诊断入口。任务执行留在主工作区，包括权限审批、Diff 审查、Patch 应用、测试结果、回滚和 Agent 运行进度。设置页可以深链接到真实工作台，但不复制工作台。

## 3. P0-1：受信 Agent Core 通道

### 3.1 当前问题

`createAgentCoreFetcher()` 对非受信 URL 回退到 renderer 普通 `fetch`。模型设置请求可包含密钥，因此错误或恶意 URL 可能将敏感请求发送到非预期地址。

### 3.2 目标数据流

```text
Desktop UI
  -> generated Agent Core client
  -> AgentCoreTransport
  -> narrow preload bridge
  -> Electron-owned endpoint and token
  -> loopback Agent Core
```

### 3.3 规则

1. 生产 transport 删除普通网络 `fetch` 回退。
2. 外部域名、错误端口、无效 URL 和非 loopback Core 地址直接拒绝。
3. Desktop 产品代码不传递 Agent Core `baseUrl`。
4. Renderer 永远不能读取 Core Token。
5. Preload 不暴露 raw `ipcRenderer`、通用 `invoke` 或通用互联网 fetch。
6. 测试通过显式 `InMemoryTransport` 或受控 mock transport 注入，不为测试保留生产逃生路径。
7. Core endpoint 在 Core 重启或端口变更后由 Electron transport 自动更新。
8. Core 未启动、Token 失效或请求超时时返回稳定的桌面错误状态，不回退到其他地址。

### 3.4 打包版 HTTP 面

`/docs`、`/redoc` 和 OpenAPI HTTP 展示入口在打包模式关闭。`/health` 可保持无密钥，但只能提供最小健康状态，不泄露配置、路径、Token 或供应商信息。其他路由继续强制 Bearer Token。

## 4. P0-2：统一凭据生命周期

### 4.1 CredentialStore interface

模型密钥只有一个存储和读取 interface：

```python
class CredentialStore(Protocol):
    def save(self, credential_id: str, secret: str) -> None: ...
    def load(self, credential_id: str) -> str | None: ...
    def delete(self, credential_id: str) -> None: ...
    def exists(self, credential_id: str) -> bool: ...
```

Adapters：

- `WindowsDpapiCredentialStore`：正式 Windows Desktop。
- `InMemoryCredentialStore`：单元测试。

阶段 A 不建立面向用户的通用密钥导出能力。

### 4.2 模型配置

非敏感配置持久化，明文密钥不进入设置 JSON：

```json
{
  "provider_id": "provider_openai",
  "provider_type": "official",
  "protocol": "openai-compatible",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "temperature": 0.2,
  "credential_id": "model.provider_openai"
}
```

`ModelSettingsStore` 不持有长期明文 `api_key`。模型调用时，gateway 通过 `CredentialStore` 按 provider 读取密钥。明文仅存在于当前进程内存中，不写日志或 trace。

### 4.3 保存、验证与删除

桌面端“保存并验证”流程：

1. 校验供应商配置和 Endpoint。
2. 将密钥写入 Windows 安全存储。
3. 保存非敏感供应商配置。
4. 获取模型列表；失败时允许进入手填模型流程。
5. 对所选模型发起一次最低成本真实请求。
6. 返回分阶段验证状态，不返回密钥。

删除供应商或密钥时，必须删除对应 credential，并立即使该供应商变为未配置。删除操作需确认并生成脱敏审计事件。

### 4.4 旧明文密钥迁移

首次运行新版本时检测 `.bolt/desktop-api-key`：

1. 读取旧密钥一次。
2. 写入 DPAPI 安全存储。
3. 重新读取并验证写入成功。
4. 原子删除旧明文文件。
5. 记录不含密钥、长度、前缀和内容的迁移结果。

若任一步失败：

- 不先删除旧文件。
- 不把旧密钥载入正常模型运行时。
- Desktop 显示“密钥迁移失败，请重新保存”。
- 阻止真实模型调用。
- Release Evidence 标记失败。

迁移过程必须支持崩溃恢复和重复执行，成功状态具有幂等性。

## 5. 模型供应商与第三方中转站

### 5.1 阶段 A 协议范围

阶段 A 只实现 OpenAI-compatible 协议：

- OpenAI 官方。
- DeepSeek 官方。
- 用户自定义 OpenAI-compatible 第三方中转站。
- 本地 OpenAI-compatible 服务。

Anthropic Messages、Gemini 原生协议不在阶段 A。第三方中转站即使提供名为 Claude 或 Gemini 的模型，只要以 OpenAI-compatible 协议暴露，Bolt 仍按 OpenAI-compatible 调用。

### 5.2 官方供应商

内置官方模板：

- OpenAI：`https://api.openai.com/v1`
- DeepSeek：`https://api.deepseek.com/v1`

官方模板的 Endpoint 不可修改。需要中转地址时，用户必须显式创建自定义供应商，避免第三方被伪装为官方。

### 5.3 自定义供应商

创建字段：

- 名称。
- Endpoint。
- API Key。
- 可选手填模型 ID。

界面必须明确提示：第三方供应商会接收提示词、代码片段和模型上下文。每个供应商使用独立 `credential_id`，不能读取其他供应商的凭据。

### 5.4 Endpoint 安全策略

- 公网 Endpoint 必须使用 HTTPS。
- HTTP 只允许 `localhost`、`127.0.0.1` 和 `::1`。
- 禁止 URL 用户名、密码、fragment 和非 HTTP(S) 协议。
- 限制 URL 长度、重定向次数、响应大小和超时。
- 保存、验证和实际调用前均执行目标校验。
- DNS 解析的全部地址均需校验。
- 拒绝云元数据、链路本地、组播、保留地址和默认私网目标。
- 公网域名解析到私网地址时拒绝。
- 每次重定向后重新解析和校验。
- 禁止访问 Bolt Agent Core 自身端口。
- 本地模型允许 loopback，但在 UI 标记为“本地”。

### 5.5 模型列表与验证

1. 首先请求 `/v1/models`。
2. 成功时最多保留 200 个合法模型 ID。
3. 不支持 `/v1/models` 时允许手动填写模型 ID。
4. 模型 ID 限制为 1–128 个合法字符。
5. 必须再执行一次最低成本模型请求，才能显示“模型调用成功”。

状态分别表示：

- `unverified`
- `reachable`
- `authenticated`
- `models_loaded`
- `verified`
- `failed`

不能只凭 Endpoint 返回 200 或 `/v1/models` 成功就显示最终绿色状态。

### 5.6 会话模型选择

主工作区输入区显示 `供应商 · 模型` 选择器。每个会话记录 `provider_id` 和 `model_id`，不记录密钥。供应商被删除时，历史会话仍保留脱敏名称，但再次运行前必须选择可用供应商。

## 6. Desktop 设置中心

### 6.1 信息架构

设置分类由 Bolt 当前真实能力生成，不由参考图菜单生成。初始候选分类：

- 常规。
- 外观。
- 工作区。
- 模型与中转站。
- Agent 行为。
- 权限与安全。
- 上下文与预算。
- Memory。
- 工具与命令。
- 技能（仅当现有能力可配置）。
- MCP 服务器（仅当现有能力可配置）。
- 多智能体（仅当现有能力可配置）。
- Git、Patch 与 Diff。
- 测试与验证。
- 审计与诊断。
- 使用统计（仅展示真实数据）。
- Agent Core。
- 数据、迁移与恢复。
- Release Evidence。
- 关于 Bolt。

实施前必须建立“现有能力 -> 可配置项 -> 真实读写来源 -> 验证方式”清单。没有真实读写来源的项目不显示。

### 6.2 无空壳规则

每个可见控件必须满足：

- 按钮触发真实行为。
- 开关写入真实配置并在重启后恢复。
- 下拉选项影响真实运行时。
- 状态来自实际 Core 或持久化数据。
- 搜索定位真实设置。
- 危险操作有确认、失败反馈和审计。
- 有 focused test 覆盖成功、失败和恢复路径。

### 6.3 模型页布局

模型页采用双栏：

- 左栏：官方供应商、自定义供应商、连接状态、“添加供应商”。
- 右栏：名称、类型、Endpoint、API Key 状态、模型列表、手填模型、默认模型、最近验证、保存并验证、删除密钥、删除自定义供应商。

官方、第三方和本地供应商必须有明显标签。API Key 永不回显。

### 6.4 主题

阶段 A 支持跟随系统、浅色和深色。布局在三种主题中保持一致。视觉风格以高可读、克制、适合长时间阅读 Diff 和 Terminal 为优先，不以透明玻璃效果牺牲信息清晰度。

## 7. Pydantic、OpenAPI 与 TypeScript 生成客户端

### 7.1 单一事实源

FastAPI Pydantic 请求/响应 DTO 是关键 Desktop interface 的唯一事实源：

```text
Pydantic DTO
  -> deterministic openapi.json
  -> generated TypeScript types/client
  -> injected AgentCoreTransport
```

### 7.2 阶段 A 迁移路由

- 供应商管理和验证。
- 模型设置。
- Harness Run。
- Agent Step / Agent Loop。
- 权限查询、批准和拒绝。
- Workspace 状态。
- Patch 提议、预览、应用和回滚。
- Release Evidence 状态。

其他历史路由保持兼容，后续增量迁移。

### 7.3 DTO 规则

安全关键 DTO：

- 禁止未知额外字段。
- 明确请求和响应类型。
- 对名称、URL、密钥、模型 ID、数组数量和文本长度设置上限。
- Secret 使用 `SecretStr` 或不进入响应 DTO。
- 错误返回稳定错误码，不向 Desktop 暴露堆栈和敏感第三方响应。

### 7.4 生成规则

建议目录：

```text
packages/agent-core-client/
  openapi.json
  src/generated/
```

- 生成文件不可手改。
- CI 重新导出和生成，并检查 Git diff。
- Schema 或生成客户端漂移使 quality gate 失败。
- Desktop 关键调用不再手写响应类型和 URL。
- 生产客户端只能注入受信 preload transport。

## 8. 错误处理与并发

### 8.1 稳定错误分类

Desktop 至少区分：

- Core 未启动或正在重启。
- Core 鉴权失败。
- 配置校验失败。
- 凭据不存在或迁移失败。
- Endpoint 被安全策略拒绝。
- DNS/TLS/连接失败。
- 第三方鉴权失败。
- 模型不存在。
- 模型列表不支持。
- 请求超时或限流。
- 供应商配置在请求期间被修改。

### 8.2 并发规则

- 同一供应商的保存、删除和验证操作按 provider 串行化。
- 每次配置变更增加 revision；旧验证结果不能覆盖新配置。
- 删除凭据后正在排队的调用必须失败，不得继续使用缓存密钥。
- Agent Core 重启期间 Desktop 显示恢复状态，不将请求发送到旧端口。
- Release Evidence 中记录状态转换，但不记录敏感内容。

## 9. 测试策略

遵循仓库规则：生产代码必须先有失败测试。

### 9.1 P0-1

- 外部 URL fail-closed。
- 错误 localhost 端口 fail-closed。
- Core Token 不暴露到 renderer。
- Core 重启后 endpoint 更新。
- 无生产普通 fetch 回退。

### 9.2 凭据

- 保存、读取、删除。
- Desktop 响应和日志不含密钥。
- 旧明文迁移成功后删除。
- 写入失败时保留旧文件。
- 迁移中断后可恢复。
- 重启后 gateway 可调用真实 provider。
- 并发保存/删除保持一致。

### 9.3 Endpoint 安全

- 公网 HTTP 被拒绝。
- loopback HTTP 被允许。
- 私网、元数据和保留地址被拒绝。
- DNS rebinding 模拟被拒绝。
- 重定向到私网被拒绝。
- Bolt Core 端口被拒绝。
- 超大模型列表和恶意模型 ID 被截断或拒绝。

### 9.4 DTO 与客户端

- 关键路由不再接受非法裸 dict。
- 请求和响应通过 Pydantic 校验。
- OpenAPI 导出确定性。
- 生成客户端无未提交漂移。
- Desktop transport 错误映射稳定。

### 9.5 Desktop 设置

每个可见控件需覆盖：

- 真实读写。
- 重启恢复。
- Loading、成功、失败和重试。
- 危险操作确认。
- 键盘可用性和基本可访问性。
- 无不可达按钮或假状态。

## 10. 干净 Windows 隔离验收

正式基线采用本机隔离验证：

- 专用全新 Windows 本地用户。
- 全新 Bolt 安装和用户数据目录。
- 不复用开发仓库 `.venv`、现有 `.bolt` 或旧运行进程。
- 使用正式 NSIS 安装包。

必须按顺序完成：

1. 安装并首次启动。
2. 打包 Python Core 自动启动。
3. 添加官方或自定义供应商。
4. 用户仅在 Bolt Desktop 本地输入 API Key。
5. 安全保存并完成真实最低成本模型调用。
6. 完全退出并确认 Core 子进程结束。
7. 重启后不重新输入密钥，模型调用仍成功。
8. 创建临时工作区并执行读取任务。
9. 提出写入，确认出现权限审批和 Diff。
10. 拒绝一次并证明文件未改变。
11. 批准一次并证明内容正确写入。
12. 执行回滚并证明恢复原内容。
13. 删除供应商并证明凭据同步删除。
14. 卸载 Bolt，检查程序文件、进程、启动项和临时资源。

卸载时工作区内容不得被静默删除。用户数据保留或删除必须由明确选项决定。

## 11. Release Evidence

每个候选构建生成唯一证据目录：

```text
release-evidence/<version>-<commit>-<timestamp>/
  manifest.json
  checks.json
  artifacts.json
  environment.json
  events.ndjson
  screenshots/
  logs/
```

### 11.1 Manifest

记录：

- Bolt 版本与 Git commit。
- 构建和验收时间。
- Windows、Node、Python、Electron 版本。
- 安装包 SHA-256。
- OpenAPI Schema SHA-256。
- 生成客户端 SHA-256。
- 最终结论。

### 11.2 Check 状态

只允许：

- `passed`
- `failed`
- `blocked`
- `not_run`

`not_run` 和 `blocked` 不计为通过。每项 check 指向具体日志、事件、截图或哈希证据。

### 11.3 脱敏

证据禁止包含：

- API Key 和 Authorization header。
- 完整提示词。
- 用户源代码正文。
- 用户名和个人路径。
- 第三方原始响应。
- Windows Credential 数据。

真实模型调用只记录匿名 provider ID、model ID、状态分类、延迟、token 数量和脱敏错误码。

## 12. 阶段 A 退出标准

只有全部满足才能标记“安全受控 Beta”：

- 两个 P0 有自动回归测试并通过。
- Agent Core 外部 URL 请求 fail-closed。
- 密钥不再存普通明文文件。
- 旧密钥迁移成功后自动删除。
- 重启后真实模型调用成功。
- 官方与第三方供应商明确区分。
- 自定义 Endpoint 通过 SSRF 防护。
- 关键 Desktop 路由使用 Pydantic 与生成客户端。
- CI 能发现 OpenAPI 漂移。
- 所有可见设置控件都接入真实能力。
- 权限拒绝、批准、Diff 和回滚真机通过。
- NSIS 安装和卸载真机通过。
- Release Evidence 完整且脱敏。
- `pnpm quality`、Desktop build、Python tests 全部通过。

## 13. 非目标

阶段 A 不包含：

- Web 管理后台。
- Anthropic/Gemini 原生协议。
- 云端账号、订阅、计费或套餐购买。
- 插件商城、宠物或外部产品特有功能。
- 将所有历史 FastAPI 路由一次性迁移。
- 自动更新上线；在签名和发布策略完成前保持关闭。
- 空壳设置页或虚构统计。

## 14. 实施分解边界

本规格较大，实施计划必须分为可独立验证的纵向切片：

1. 受信 Desktop transport。
2. CredentialStore 与旧密钥迁移。
3. Provider registry、Endpoint 安全和真实验证。
4. Pydantic/OpenAPI 与生成客户端。
5. Desktop 模型页和会话模型选择。
6. Bolt 真实能力设置清单与设置接线。
7. Release Evidence 生成器。
8. Windows 隔离验收与最终放行。

每个切片先写失败测试，经过 focused verification 后再进入下一切片。不得在已有未提交 UI 修改上做无关重构。
