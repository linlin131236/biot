# M137 Atomic Write Apply 执行计划

## 背景

外部复审指出 `patch_engine.py` 与 `approval_apply.py` 使用裸 `write_text()` 覆盖目标文件。若写入或替换过程中失败，可能留下半写入文件，尤其会影响已获批准的补丁应用链路。

## 目标

1. 为批准后的文件写入增加原子替换语义。
2. `patch_engine.apply_change_set()` 写入失败时保留原文件。
3. `ApprovalApplyEngine.apply()` 写入失败时保留原文件，并返回失败。
4. 不改变 PermissionGate、审批和路径安全语义。

## 非目标

- 不新增自动 apply。
- 不新增 delete/push/release/tag 能力。
- 不改变 diff 解析策略。
- 不做大规模补丁引擎重构。

## 实施步骤

1. 先增加 `os.replace` 失败时原文件保持不变的红灯测试。
2. 新增共享 `atomic_write_text()`。
3. `patch_engine.py` 改用原子写。
4. `approval_apply.py` 改用原子写，并保持 modify 缺失文件失败。
5. 跑 targeted tests、full tests、quality、build 和安全扫描。

## 验收标准

- 模拟 `os.replace` 失败时，原文件内容不变。
- `apply_change_set()` 返回失败原因，不抛出未处理异常。
- `ApprovalApplyEngine.apply()` 返回失败原因，不标记 proposal applied。
- 所有既有补丁应用测试保持通过。
