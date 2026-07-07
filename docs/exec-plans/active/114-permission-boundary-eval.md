# M114 Exec Plan — 权限边界评估

## 参考资料
- 复用 M103 tool_permission_contract.py（PermissionContractEngine）
- 复用 M111 tool_call_eval.py 的 _build_eval_registry()

## 新增文件
- `services/agent-core/src/bolt_core/permission_boundary_eval.py`
- `services/agent-core/src/bolt_core/permission_boundary_eval_api.py`
- `services/agent-core/tests/test_permission_boundary_eval.py`

## 验收
- ≥12 eval cases, dangerous全阻断, false approval全阻断, secret全阻断, API只读
