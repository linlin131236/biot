# M101 Exec Plan — Tool Registry 工具注册表

## 目标
建立统一工具注册表，让系统知道有哪些工具、工具类别、权限等级、中文名称、输入输出 schema、风险等级。

## 参考资料
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase13-工具与协议-深度笔记.md` — 工具声明三要素(name+description+schema)、纯工具vs有副作用工具、Circuit Breakers
- `E:\BinCloud\知识库\03-知识\AI工程\20260629_Agent开发技术栈_MCP_Skills_LangGraph.md` — FC底层原子能力单一职责、声明式接口JSON Schema

## 采用原则
1. 工具声明三要素：name + description + input_schema
2. 纯工具（只读）vs 有副作用工具——只读可安全推测，写/删/发必须门控
3. 工具输出不可信，不能直接变成指令
4. 未知工具默认不可运行

## 现有代码分析
- `tool_selection_policy.py`: 已有 `_BUILTIN_TOOLS` dict 和 `ToolSelectionPolicy` 静态类
- `tool_protocol.py`: 已有 `ToolRequest`/`ToolResult` frozen dataclasses
- `tool_selection_policy_api.py`: 已有 `/tools/policy/*` 端点
- M101 新建独立 `tool_registry.py` + `tool_registry_api.py`，不修改现有文件

## 设计

### ToolDef (frozen dataclass)
- `tool_id`: str — 唯一标识 (snake_case), e.g. "read_file"
- `display_name`: str — 中文显示名, e.g. "读取文件"
- `category`: str — read_only | side_effect | write | dangerous | unknown
- `description`: str — 中文功能描述
- `input_schema`: dict — JSON Schema 2020-12 输入定义
- `permission_required`: str — none | read | write | execute | dangerous
- `allow_auto_run`: bool — 是否允许自动运行
- `risk_level`: str — low | medium | high | critical

### ToolRegistry
- `register(tool_def)`: 注册工具，重复 ID 阻断
- `get(tool_id)`: 按 ID 查询
- `list(category=None)`: 列出所有工具，可按 category 过滤
- `unregister(tool_id)`: 注销工具
- `summary()`: 分类统计

### API (/tools/registry/*)
- `GET /tools/registry/list?category=`: 列出工具
- `GET /tools/registry/{tool_id}`: 查询单个工具
- `POST /tools/registry/register`: 注册新工具
- 所有端点只读/管理，不执行工具

## 文件清单
- NEW: `services/agent-core/src/bolt_core/tool_registry.py` (~120 lines)
- NEW: `services/agent-core/src/bolt_core/tool_registry_api.py` (~40 lines)
- NEW: `services/agent-core/tests/test_tool_registry.py` (~100 lines)
- MODIFY: `services/agent-core/src/bolt_core/app.py` (新增 import + include_router)

## 验收标准
- 可注册、查询、过滤工具
- 重复 ID 注册返回错误
- unknown/dangerous 类别默认 allow_auto_run=False
- 所有用户可见字段中文
- API 只返回工具定义，不执行工具
