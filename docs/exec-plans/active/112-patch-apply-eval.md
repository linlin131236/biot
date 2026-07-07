# M112 Exec Plan — 补丁应用评估

## 参考资料
- `AI工程-Phase13-工具与协议-深度笔记.md`：工具安全原则、副作用门控
- 复用 M108 approval_apply.py 的 ApprovalApplyEngine + WriteProposalStore

## 新增文件
- `services/agent-core/src/bolt_core/patch_apply_eval.py`（~200行）
- `services/agent-core/src/bolt_core/patch_apply_eval_api.py`（~45行）
- `services/agent-core/tests/test_patch_apply_eval.py`（~160行）

## 实现方案
1. **PatchApplyEvalCase**：定义 eval case（case_id, description, setup_fn, expected_success, expected_reason_keyword）
2. **PatchApplyEvalService**：在临时目录中运行 eval cases，验证 ApprovalApplyEngine.apply() 行为
3. 至少10个 eval cases：单文件修改、新建文件、多文件修改、diff不匹配、注入额外文件、.env路径阻断、.claude路径阻断、stale proposal、agent self-approval、scope mismatch
4. API只读查询：GET /tools/eval/patch-apply/run, GET /tools/eval/patch-apply/summary

## 验收标准
- 至少10个 eval cases
- 成功/失败路径都有
- 多文件串改回归测试存在
- 所有失败有中文原因
- API只读
