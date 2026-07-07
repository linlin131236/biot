# M102 Decision — Tool Manifest 工具能力声明

## 决策
采用 `ToolManifest` frozen dataclass + `ToolManifestValidator` 独立验证器，不混入 registry 逻辑。

## 理由
1. **关注点分离**：Registry 管注册，Manifest 管能力声明和验证，各自聚焦。
2. **两层验证**：先做结构验证（字段完整性），再做注册表交叉验证（一致性），分步诊断。
3. **危险工具强制声明**：`human_approval_required` 和 `approval_scope` 是危险工具的必填字段。
4. **权限一致的强制检查**：manifest 的 `permission_contract.required_level` 必须与 registry 的 `permission_required` 一致。
5. **不执行工具**：所有验证端点只产出 validation result，不触发任何工具调用。

## 测试覆盖
- 22 tests：ToolManifest dataclass (5)，结构验证 (9)，注册表交叉验证 (5)，ValidationResult (1)
