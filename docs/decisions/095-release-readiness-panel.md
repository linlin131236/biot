# M95 Decision - 发布准备页

## 决策
发布准备页复用已有 release readiness API，只做中文可视化，不提供发布、tag、push、delete 按钮。

## 原因
发布检查和发布动作必须分离。检查页可以告诉爸爸是否 ready，但不能替爸爸执行危险操作。

## 结果
- ready/blocker/warning 更容易理解。
- 继续遵守不自动 push/release/tag/delete 的硬规则。
