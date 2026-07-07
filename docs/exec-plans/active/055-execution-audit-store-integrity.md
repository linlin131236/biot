# M55 Execution Plan: Execution Audit Store Integrity Guard

## 目标
为 execution-audit.json 增加完整性保护：读写时校验结构、避免半写入破坏、发现损坏时给出清晰只读诊断，不自动修复、不执行任何命令。

## 范围
- 后端为主：新增 integrity service + API
- 前端：新的只读展示面板
- 不新增执行能力、不新增 approve/reject 入口、不做自动修复按钮

## 验收标准
1. audit file 不存在 → 返回 healthy / 空状态
2. audit file JSON 损坏 → API 返回中文错误，不让 app 整体 500 崩掉
3. queue_items / handoff_records / closure_records 类型不对 → 返回 blocking diagnostic
4. queue/handoff/closure 正常 → 返回 clean
5. 保存 queue 不丢 handoff/closure（已有行为，integrity 验证确认）
6. 保存 handoff 不丢 queue/closure（同上）
7. 保存 closure 不丢 queue/handoff（同上）
8. integrity API 只读，不写文件、不修复文件、不执行命令
9. UI 只读展示"审计文件正常 / 审计文件损坏 / 需要人工处理"

## 实现步骤
1. 写 exec plan 和 decision 文档
2. 写失败测试：
   - test_execution_audit_integrity.py：integrity service 测试
   - test_execution_audit_integrity_api.py：API 端点测试
   - 扩展 test_execution_audit_store.py：三类记录互不覆盖
3. 实现 execution_audit_integrity.py
4. 实现 execution_audit_integrity_api.py
5. 修改 app.py 接 router
6. 修改 protocol-autonomy.ts 增加 integrity 类型
7. 修改 harnessClientAutonomy.ts 增加 fetchExecutionAuditIntegrity
8. 修改 ExecutionHandoffPanel.tsx 展示中文完整性状态
9. 跑测试验证
10. 更新 docs/phase-55-review-gate.md 和 docs/project-state.md
11. 自审 diff 并 commit

## 涉及文件
- 新增：services/agent-core/src/bolt_core/execution_audit_integrity.py
- 新增：services/agent-core/src/bolt_core/execution_audit_integrity_api.py
- 修改：services/agent-core/src/bolt_core/app.py
- 修改：packages/shared/src/protocol-autonomy.ts
- 修改：apps/desktop/src/harnessClientAutonomy.ts
- 修改：apps/desktop/src/ExecutionHandoffPanel.tsx
- 新增：services/agent-core/tests/test_execution_audit_integrity.py
- 新增：services/agent-core/tests/test_execution_audit_integrity_api.py
- 修改：services/agent-core/tests/test_execution_audit_store.py（扩展）

## 不修改
- execution_audit_store.py（其自身行为已满足保存互不覆盖要求）
- PermissionGate
- renderer 能力
