# M123 Update Rollback Exec Plan

## 目标
为 Beta 前升级、回滚和发布建立只读准备度门禁，确保更新必须人工确认、可验证、可回滚。

## 参考资料
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase17-基础设施与生产-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第27章-规模化运维.md`

采用原则：平台化运维要把人工协调变成一致门禁，但不能把危险动作变成自动执行。

## 实现范围
- 新增 `update_rollback.py`：检查发布准备、恢复策略、批准边界和测试运行器。
- 新增 `update_rollback_api.py`。
- 新增 `docs/release/update-rollback-plan.md`。
- 新增目标测试和 API 测试。

## 验收
- 发布准备门禁必须存在。
- 回滚策略必须存在。
- 升级/回滚计划必须写明 manual、update、rollback、approval。
- 不允许 automatic release 或 auto release。
