# M113 Decision — 测试失败诊断评估

## 决策
建立 FailureDiagnosisEvalService，使用固定失败样例验证系统能正确归类、脱敏、生成中文诊断。

## 设计选择
1. **8 个固定失败样例**：pytest assertion, import error, timeout, vitest failure, build error, permission denied, secret in log, syntax error
2. **关键词匹配 + 秘密检测**：`_diagnose()` 按优先级匹配关键词确定类别，`_has_secrets()` 用正则检测密钥/令牌
3. **输出脱敏**：6 种 secret pattern（API key, GitHub token, Bearer token, password, secret, private key）
4. **is_auto_fix_allowed=False**：所有诊断禁止自动修复
5. **API 只读**：GET /tools/eval/failure-diagnosis/run

## 风险
- 低：纯评估模块，不执行修复
