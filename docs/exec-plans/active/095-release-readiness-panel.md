# M95 Exec Plan - 发布准备页

## 目标
把已有 release readiness 结果做成中文桌面页，让爸爸能看懂是否可发布、哪里阻断、哪些只是警告。

## 参考资料
- Agent产品化流水线：发布前检查必须可验证、可追溯。
- 桌面AI编程Agent全流程架构对比：发布动作不得混入检查页。

## 实施
- 新增 `ReleaseReadinessPanel.tsx` 和测试。
- 复用已有 `release_readiness_api.py`，不新增发布、tag、push 入口。
- 展示 ready、blockers、warnings、checks。

## 验收
- 只读中文 UI。
- 无 release/push/tag/delete 按钮。
- 测试覆盖 ready 与 blocker 状态。
