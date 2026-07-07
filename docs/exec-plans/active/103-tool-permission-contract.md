# M103 Exec Plan — Tool Permission Contract 工具权限契约

## 目标
把工具调用和 PermissionGate 绑定，明确什么工具需要什么批准，不能靠调用方绕过。

## 参考资料
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase13-工具与协议-深度笔记.md` — Pure vs Side-effect tools, Circuit Breakers, Rule of Two
- `E:\BinCloud\知识库\03-知识\AI工程\20260629_Agent开发技术栈_MCP_Skills_LangGraph.md` — FC底层原子能力

## 设计

### Permission Levels
- `none`: 纯展示、纯内存计算
- `read`: 读文件、读 git、读项目状态
- `write`: 修改文件、写补丁、保存配置
- `execute`: 运行测试、运行命令
- `dangerous`: delete、release、tag、push、凭证

### ToolPermissionContract (frozen dataclass)
- `tool_id`, `required_level`, `human_approval_required`, `approval_scope`
- `forbidden_ops`: 该工具绝对不能执行的操作列表

### PermissionDecision (frozen dataclass)
- `tool_id`, `decision` (allowed/denied/needs_approval), `reason` (Chinese)
- `required_approval_by`: who must approve (human/father)

### PermissionContractEngine
- `evaluate(tool_id, registry, manifest)`: 评估工具是否需要批准
- `verify_approval(decision, approval_record)`: 验证批准是否有效
- 拒绝 `approved=true` 直传绕过
- 拒绝 agent self-approval
- 拒绝 scope 不匹配

## API
- `POST /tools/permission/evaluate`: 评估工具权限需求
- `POST /tools/permission/verify`: 验证批准记录

## 文件
- NEW: `tool_permission_contract.py` (~130 lines)
- NEW: `tool_permission_contract_api.py` (~40 lines)
- NEW: `tests/test_tool_permission_contract.py` (~100 lines)
- MODIFY: `app.py`
