# M113 Exec Plan — 测试失败诊断评估

## 参考资料
- 复用 M64 failure_classifier.py（CATEGORIES、_CATEGORY_META）
- 复用 M109 test_runner_integration.py（结果结构）

## 新增文件
- `services/agent-core/src/bolt_core/test_failure_diagnosis_eval.py`（~180行）
- `services/agent-core/src/bolt_core/test_failure_diagnosis_eval_api.py`（~45行）
- `services/agent-core/tests/test_test_failure_diagnosis_eval.py`（~130行）

## 实现方案
1. 固定失败样例（≥8个）：pytest assertion, import error, timeout, vitest failure, build error, permission denied, secret in log, syntax error
2. 诊断输出：failure_category, likely_cause, recommended_next_step, redacted_output, confidence, is_auto_fix_allowed=false
3. 不自动修复
4. API只读

## 验收
- ≥8 failure cases, secret脱敏, 中文建议, auto_fix=false, API只读
