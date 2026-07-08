# M133 Decision: Fake 只允许显式选择

## 决策

引入 `DefaultModelGateway`：

- `provider == "fake"` 时使用 `FakeModelGateway`。
- 其他 provider 默认使用 `OpenAICompatibleGateway`。
- 默认模型设置改为 `openai-compatible`，无 API key 时明确返回 `api key missing`。

## 原因

Biot 的产品目标是桌面 AI 编程 Agent。生产默认使用 fake 会制造“看起来能跑”的错觉，尤其会伪造工具调用，掩盖真实模型配置缺失。

## 取舍

- 保留 fake provider：测试、dogfood 和离线演示仍需要稳定可控的模型响应。
- 不自动读取仓库内密钥文件：API key 只能来自用户设置或运行环境。
- 不在本 milestone 做模型供应商持久化：先修正执行真实性，再做体验层。

## 风险

- 新用户未配置模型时，agent step 会失败而不是假装执行。前端需要在后续体验中把这个失败说明得更清楚。
- 部分旧测试必须显式设置 fake，这属于合理收紧。

