# M102 Exec Plan — Tool Manifest 工具能力声明

## 目标
建立工具 manifest 格式，描述每个工具能做什么、需要什么权限、会产生什么副作用。

## 参考资料
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase13-工具与协议-深度笔记.md` — 工具声明三要素、schema validation、pure vs side-effect
- `E:\BinCloud\知识库\03-知识\AI工程\20260629_Agent开发技术栈_MCP_Skills_LangGraph.md` — 声明式接口JSON Schema定义

## 采用原则
1. 工具声明三要素：name + description + input_schema
2. 有副作用工具必须门控
3. manifest 必须可验证，缺字段必须失败
4. 权限声明和 registry 冲突必须失败

## 设计

### ToolManifest (frozen dataclass)
- `tool_id`: str — 对应 ToolRegistry 中的 tool_id
- `version`: str — 语义版本
- `display_name`: str — 中文 UI 标签
- `capability_summary`: str — 中文能力描述
- `input_schema`: dict — JSON Schema
- `output_schema`: dict — JSON Schema
- `side_effect_level`: str — none | read_only | side_effect | write | dangerous
- `permission_contract`: dict — {required_level, human_approval_required, approval_scope}
- `audit_requirements`: dict — {log_calls, log_results, evidence_required}
- `rollback_support`: bool — 是否支持回滚

### ToolManifestValidator
- `validate(manifest)`: 检查所有必填字段
- `validate_against_registry(manifest, registry)`: 检查权限声明与 registry 一致性
- dangerous 工具缺少人工确认声明 → 失败

### API
- `POST /tools/manifest/validate`: 验证 manifest
- `GET /tools/manifest/{tool_id}`: 查询工具 manifest（需先在 registry）

## 文件清单
- NEW: `services/agent-core/src/bolt_core/tool_manifest.py` (~130 lines)
- NEW: `services/agent-core/src/bolt_core/tool_manifest_api.py` (~35 lines)
- NEW: `services/agent-core/tests/test_tool_manifest.py` (~100 lines)
- MODIFY: `services/agent-core/src/bolt_core/app.py`
