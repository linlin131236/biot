# M122 Data Migration Exec Plan

## 目标
为 Beta 前数据迁移建立只读准备度门禁，确认 Context Lakehouse 的 raw、staging、clean、lineage 和人工回滚原则已经写清。

## 参考资料
- `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase17-基础设施与生产-深度笔记.md`
- `E:\BinCloud\知识库\03-知识\AI工程\哈佛CS249r-第27章-规模化运维.md`

采用原则：迁移必须先演练、可回滚、可追踪依赖；当前阶段不自动迁移真实数据。

## 实现范围
- 新增 `data_migration.py`：只读检查迁移计划和数据层依赖。
- 新增 `data_migration_api.py`。
- 新增 `docs/release/data-migration-plan.md`。
- 新增目标测试和 API 测试。

## 验收
- 迁移计划必须包含 raw/staging/clean/lineage。
- 迁移计划必须包含 rollback 和 manual/approval/dry-run。
- 不允许自动迁移。
