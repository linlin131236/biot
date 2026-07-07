# M64 执行计划：Failure Classification

## 目标
建立失败分类机制，输出中文原因和建议，不自动修复。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_AgentHarness20层进化指南.md`：s11 错误恢复

## 实现方案

### 后端
- `bolt_core/failure_classifier.py`：FailureClassifier
  - 8 种分类：用户输入问题、权限等待、工具失败、测试失败、网络失败、代码质量失败、安全阻断、未知
  - 关键词匹配分类算法
  - 每个分类：中文标签、中文建议、是否可重试、禁止自动修复
- `bolt_core/failure_classifier_api.py`：
  - GET /failure/categories
  - POST /failure/classify
  - POST /failure/is-retryable

## 验收标准
- [x] 8 种失败分类 + 全中文标签/建议
- [x] 关键词匹配覆盖主要错误模式
- [x] 所有分类 auto_fix_possible = False
- [x] 19 个 targeted tests
