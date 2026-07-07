# M111 Exec Plan — 工具调用评估基准

## 参考资料
- `AI工程-Phase13-工具与协议-深度笔记.md`：工具声明三要素（name/description/input_schema）、纯工具vs有副作用工具、Rule of Two、Circuit Breakers
- `20260629_Agent开发技术栈_MCP_Skills_LangGraph.md`：FC→Skills→MCP三层、自上而下依赖、禁止反向依赖

**采用原则**：
1. 每个工具必须有明确schema和类别
2. 只读工具可自动通过；有副作用工具需要门控
3. dangerous操作（push/release/tag/delete/credential）永远阻断
4. 未知工具默认拒绝
5. 评估不执行真实工具，只做选择/判断

## 新增文件
- `services/agent-core/src/bolt_core/tool_call_eval.py`（~180行）
- `services/agent-core/src/bolt_core/tool_call_eval_api.py`（~45行）
- `services/agent-core/tests/test_tool_call_eval.py`（~160行）

## 实现方案
1. **EvalCase frozen dataclass**：user_intent, expected_category, allowed_tools, forbidden_tools, expected_permission, needs_human_approval, chinese_explanation
2. **EvalResult frozen dataclass**：case_id, selected_tool_correct, permission_correct, dangerous_blocked, explanation_zh, overall_passed
3. **ToolCallEvalService**：使用ToolRegistry注册标准工具集，对每个case评估PermissionContractEngine.evaluate()结果
4. 至少12个eval cases覆盖：读文件、git status、生成补丁、apply补丁、跑测试、push/release/tag/delete拒绝、secret文件读取拒绝、未知工具拒绝
5. API只读查询：GET /tools/eval/list, GET /tools/eval/result/{case_id}, GET /tools/eval/summary

## 验收标准
- 至少12个eval cases
- dangerous案例全部blocked
- unknown工具不得自动通过
- 输出全中文摘要
- API只读
