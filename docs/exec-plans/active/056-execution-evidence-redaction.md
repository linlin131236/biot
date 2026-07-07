# M56 Execution Plan: Execution Evidence Redaction

## 目标
引入保守脱敏层，防止 token、API key、证书片段、环境变量、长输出直接进入持久化审计或 UI 展示。

## 范围
- 只处理写入 audit store / closure evidence / timeline summary 的字符串
- 不改变真实命令执行
- 不隐藏命令本身，除非命令里明显带 secret
- 不做复杂正则宇宙，只覆盖明确高风险模式

## 实现步骤
1. 写 exec plan 和 decision 文档
2. 新增 evidence_redactor.py：`redact(text) -> str` 函数
3. 修改 task_closure_service.py：写 commands/command_results 前调用 redactor
4. 修改 execution_handoff.py：写 result/bridge_error 前调用 redactor
5. 修改 execution_audit_timeline.py：生成 summary 前对 command/result 脱敏
6. 写测试并验证
7. 更新 docs

## 涉及文件
- 新增：services/agent-core/src/bolt_core/evidence_redactor.py
- 修改：services/agent-core/src/bolt_core/task_closure_service.py
- 修改：services/agent-core/src/bolt_core/execution_handoff.py
- 修改：services/agent-core/src/bolt_core/execution_audit_timeline.py
- 新增：services/agent-core/tests/test_evidence_redactor.py
- 新增：services/agent-core/tests/test_execution_evidence_redaction.py
- 新增：docs/exec-plans/active/056-execution-evidence-redaction.md
- 新增：docs/decisions/056-execution-evidence-redaction.md
- 修改：docs/project-state.md

## 不修改
- shell_executor.py（保留 MAX_OUTPUT_BYTES，不扩大输出）
- 真实命令执行流程
- PermissionGate
