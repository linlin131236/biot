# M64 决策：Failure Classification

## 决策
新增 FailureClassifier，基于关键词匹配做失败分类，输出中文诊断和建议。

## 关键设计选择

### 1. 关键词匹配而非 ML/AI 分类
选择简单的关键词匹配算法：
- 分类结果是确定性的，便于测试和审计
- 不依赖外部模型或 API
- 关键词可随经验积累逐步扩展

### 2. 8 种分类覆盖
- user_input：输入问题（参数缺失、格式错误）
- permission_waiting：等待人工批准
- tool_failure：工具执行返回错误
- test_failure：自动化测试不通过
- network_failure：网络连接问题
- code_quality：lint/build/type 检查失败
- security_block：安全策略阻断
- unknown：兜底

### 3. 禁止自动修复
每个分类的 auto_fix_possible 均为 False。分类器的职责是"解释和给建议"，不是"自动修"。这与 Harness 指南 s11（错误恢复）对齐——恢复步骤由人类决策，不是自动触发。

## 不做的
- 不自动重试（留给 M65）
- 不自动修复
- 不绕过 PermissionGate
