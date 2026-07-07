# M54 Recovery Dogfood + Release Hardening

## 验收标准
- 完整 dogfood 覆盖 run + closure -> missing evidence -> execution queue -> approve queue -> handoff -> request permission -> audit timeline 等待权限。
- 模拟重启后 pending permission 丢失，再次 request-permission 安全生成新 pending。
- approve permission 后 result ingestion 写回 queue completed / handoff completed / closure evidence。
- diagnostics 返回 clean。
- post assessment completed。
- 全程不自动 approve、不绕过 PermissionGate、不启动 Agent Loop、不创建 goal。

## 最小边界
- 优先新增 e2e 测试证明 M51-M53 串联。
- 不新增产品执行能力，不新增 UI 入口。
- 如果发现真实缺口，只做支撑 dogfood 的最小修复。

## 验证
- 新增 `tests/test_execution_recovery_dogfood_e2e.py`。
- 跑文档要求的后端、前端/共享、质量门和敏感扫描矩阵。
