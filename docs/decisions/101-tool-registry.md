# M101 Decision — Tool Registry 工具注册表

## 决策
采用独立 `ToolRegistry` 类 + frozen `ToolDef` dataclass，不修改现有 `tool_selection_policy.py`。

## 理由
1. **关注点分离**：`ToolSelectionPolicy` 专注于工具分类和选择验证，`ToolRegistry` 专注于工具定义的注册和查询管理。
2. **扩展性**：`ToolDef` 包含 category、permission_required、allow_auto_run、risk_level 等富字段，比 `_BUILTIN_TOOLS` 的简单 dict 更适合后续 M102-M109 的权限契约和提案系统。
3. **API 独立**：注册表有独立的 REST 端点（`/tools/registry/*`），与现有的 `/tools/policy/*` 不冲突。
4. **frozen dataclass**：`ToolDef` 不可变，但 `input_schema`/`output_schema` 中的 dict 字段导致不可 hash（可接受，实际使用中不需要 set/dict key）。

## 关键设计决策
- `category` 保留五个值：read_only / side_effect / write / dangerous / unknown（比 `ToolSelectionPolicy` 多一个 `write`）
- `allow_auto_run` 默认 False：unknown 和 dangerous 工具必须显式设为 True 才能自动运行
- `permission_required` 五级：none / read / write / execute / dangerous
- API 全部只读：register 端点仅管理定义，不执行工具
- 重复 ID 注册返回 409 Conflict

## 测试覆盖
- 25 tests：ToolDef 校验（7），注册/查询/列表/注销/统计（15），分类/权限/风险（3）
