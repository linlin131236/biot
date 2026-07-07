# M65 执行计划：Safe Retry Loop

## 目标
建立安全重试循环，只在明确安全条件下允许受控重试。

## 参考资料
- M64 Failure Classifier：提供 retryable 判断
- M63 Tool Selection Policy：提供工具危险度分类

## 实现方案

### 后端
- `bolt_core/safe_retry_loop.py`：
  - SafeRetryPolicy.assess()：评估是否可重试
    - 禁止类别：security_block, permission_waiting
    - 禁止工具：dangerous 类
    - 最大次数约束（默认 3）
  - SafeRetryLoop：跟踪重试历史
    - record_retry / can_retry / summary
- `bolt_core/safe_retry_loop_api.py`：
  - POST /retry/assess
  - POST /retry/record

## 验收标准
- [x] 安全阻断/权限等待禁止重试
- [x] 危险工具禁止重试
- [x] 最大次数限制
- [x] 重试审计历史记录
- [x] 20 个 targeted tests
