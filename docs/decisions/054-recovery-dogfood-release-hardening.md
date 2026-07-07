# Decision 054: Recovery Dogfood + Release Hardening

## 决策
用一个后端 e2e dogfood 测试串联 M51-M53：审计时间线、权限请求恢复、审计一致性诊断，并执行最终质量门。

## 原因
M51-M53 分别提供只读可视化、重启恢复和诊断能力。M54 需要证明这些能力在真实闭环中协同工作，且没有引入自动执行、自动批准或 PermissionGate 绕过。

## 约束
- 不自动 approve PermissionGate。
- request-permission 只创建 pending permission。
- approve_permission/reject_permission 只能走既有 PermissionGate 路径。
- 不启动 Agent Loop，不创建 goal。
- 不 push、release、tag、delete。

## 方案
- 新增 `test_execution_recovery_dogfood_e2e.py`。
- 测试内 monkeypatch executor 为确定性输出，不改产品代码为 fake。
- 更新 phase gate 和 project state，完成到 M54 后等待爸爸审核，不进入 M55。
