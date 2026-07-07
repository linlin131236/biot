# M111 Decision — 工具调用评估基准

## 决策
建立 ToolCallEvalService，使用 ToolRegistry + PermissionContractEngine 对固定案例集进行工具选择和权限判断评估。

## 设计选择
1. **不执行真实工具**：eval 只验证 PermissionContractEngine.evaluate() 的返回结果，不触发任何文件读写或子进程
2. **标准工具注册表**：`_build_eval_registry()` 构建 12 个代表性工具覆盖全部 4 个 category（read_only / side_effect / write / dangerous）
3. **14 个 eval cases**：覆盖读文件、git status、生成补丁、apply 补丁、跑测试、push/release/tag/delete 拒绝、secret 读取拒绝、未知工具拒绝、凭证写入拒绝、自动发布拒绝
4. **dangerous_blocked 判定**：对已注册 dangerous 工具检查 human_approval_required；对未注册工具检查 decision=DENIED
5. **API 只读**：GET /tools/eval/cases, /tools/eval/run, /tools/eval/run/{case_id}

## 排除
- 不评估具体路径级别的安全（由 ReadOnlyToolRunner PathGuard 负责）
- 不评估补丁内容正确性（由 M112 patch_apply_eval 负责）
- 不执行真实工具或修改任何文件

## 风险
- 低风险：纯评估模块，只读查询，不产生副作用
