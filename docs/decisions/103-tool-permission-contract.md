# M103 Decision — Tool Permission Contract 工具权限契约

## 决策
采用 `PermissionContractEngine` 静态评估引擎 + `PermissionDecision`/`ApprovalVerification` 不可变结果。

## 关键设计
1. **权限五级**：none → read → write → execute → dangerous
2. **write/execute/dangerous 强制人工批准**：`human_approval_required=True`
3. **永久危险操作列表**：push/release/tag/delete/credential_*/secret_*/permission_bypass 等，不依赖 registry 即判定为 dangerous
4. **批准验证五道关**：approval存在性 → approved=true绕过检测 → actor人类检测 → scope匹配 → 伪造检测
5. **不允许自作主张**：`approved=true` 无 actor → 拒绝；agent actor → 拒绝；scope 不匹配 → 拒绝
6. **纯决策不执行**：所有方法只产出 decision/verification，不触发任何工具调用

## 测试覆盖
- 24 tests：决策 dataclass (2)，未知工具拒绝 (2)，只读允许 (2)，写入需批准 (2)，危险需批准 (2)，永久危险操作 (3)，批准验证 (7)，危险操作列表 (2)，ApprovalVerification (1)
