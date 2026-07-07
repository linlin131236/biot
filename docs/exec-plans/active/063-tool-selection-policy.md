# M63 执行计划：Tool Selection Policy

## 目标
建立工具选择策略层，判断应该选什么工具，区分只读/副作用/危险工具。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`：工具层加固 checklist
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_AgentHarness20层进化指南.md`：s02 工具分发、s03 权限

## 实现方案

### 后端
- `bolt_core/tool_selection_policy.py`：ToolSelectionPolicy
  - 内置 26 种工具注册表，分 3 类：
    - 只读工具（9 种）：read_file, list_files, grep, git_status 等
    - 副作用工具（7 种）：write_file, edit_file, git_commit, npm_install 等
    - 危险工具（9 种）：git_push, git_delete, shell_exec, release 等
  - classify / list / select 方法
  - 未知工具拒绝执行
- `bolt_core/tool_selection_policy_api.py`：
  - GET /tools/policy/summary
  - GET /tools/policy/classify/{name}
  - GET /tools/policy/list?tool_class=
  - POST /tools/policy/select

## 验收标准
- [x] 26 种工具分类注册
- [x] 只读/副作用/危险/未知 四级分类
- [x] 副作用和危险工具标记 requires_permission
- [x] 未知工具拒绝（allowed=false）
- [x] 21 个 targeted tests
