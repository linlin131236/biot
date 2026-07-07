# M94 Exec Plan - 诊断中心

## 目标
把执行诊断、审计完整性和阻断项集中到中文诊断中心，优先解释“为什么不能继续”。

## 参考资料
- OpenClaw实际场景学习报告：失败必须给中文原因、影响和建议动作。
- Agent产品化流水线：诊断中心只判断，不自动修复。
- ZCode看板法：阻断项必须清楚标注 owner 和验收口径。

## 实施
- 新增 `DiagnosticsCenterPanel.tsx` 和测试。
- 新增 `diagnostics_center_api.py`，聚合诊断与完整性结果。
- 面板只读展示 blocking/warning/info，不提供自动修复按钮。

## 验收
- 中文显示阻断、警告、建议动作。
- API 与面板测试覆盖空态和有诊断项。
- 无自动执行或自动批准。
