# M124 Privacy Security Audit Exec Plan

## 目标
完成 Beta 前隐私、安全、供应链和权限边界总审计，确保所有风险信号只读、可解释，不能替代 PermissionGate。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第30章-安全与隐私.md`
- `docs/references/anthropic-jlens-global-workspace-2026.md`

采用原则：安全和隐私是发布前提，不是补丁；内部意图或风险信号只能辅助审计，不能自动执行或自动批准。

## 实现范围
- 新增 `privacy_security_audit.py`：检查脱敏、权限边界、renderer 暴露、类型逃逸、安全审计文档。
- 新增 `privacy_security_audit_api.py`。
- 新增 `docs/release/privacy-security-audit.md`。
- 新增目标测试和 API 测试。

## 验收
- renderer 不暴露 ipcRenderer/fs/shell/process。
- 无 `as any` / `unknown as`。
- 安全审计覆盖 prompt injection、permission、secret、supply chain、privacy、readonly。
- 不替代 PermissionGate。
