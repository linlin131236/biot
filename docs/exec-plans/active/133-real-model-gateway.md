# M133 Real Model Gateway 执行计划

## 背景

外部审计指出生产路径仍可能默认使用 `FakeModelGateway`。经核验，真实 `OpenAICompatibleGateway` 已存在，但 `ModelSettingsStore` 默认配置为 `provider=fake`，且 `AgentLoop()` 默认直接构造 `FakeModelGateway`。

## 目标

1. 生产默认不再走 fake 模型。
2. 缺少 API key 时明确失败，不伪造 tool call。
3. `provider=fake` 仍可作为测试/开发显式选择。
4. App 层 agent step 默认缺 key 时 fail closed。

## 非目标

- 不在本 milestone 做多轮 tool result 回填，那是 M134。
- 不持久化模型设置。
- 不引入新的模型供应商 UI。

## 实施步骤

1. 新增 `DefaultModelGateway`，按 provider 分发。
2. `AgentLoop` 默认使用 `DefaultModelGateway`。
3. `ModelSettingsStore` 默认改为 `openai-compatible` + 无 API key。
4. 更新旧 happy-path 测试，显式选择 fake。
5. 新增 fail-closed 测试。

## 验收标准

- 默认模型配置不是 fake。
- 默认 AgentLoop 缺 key 时失败，且不启动任何 tool execution。
- 显式 `provider=fake` 时测试仍可走 fake tool call。
- 模型设置 API 不泄露 API key。

