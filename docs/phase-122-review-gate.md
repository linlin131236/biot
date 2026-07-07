# M122 Review Gate - Data Migration

结论：M122 数据迁移准备度门禁通过后，才允许进入 M123。

门禁：
- 原始审计存储存在。
- 上下文压缩和线程交接摘要存在。
- 记忆权限边界存在。
- 项目画像和代码地图存在。
- 迁移计划包含 raw/staging/clean/lineage。
- 迁移计划包含人工回滚和演练。
- M122 文档链完整。
- project-state 标记 M122，且未进入 M123。

禁止项：
- 不自动迁移。
- 不直接写数据。
- 不绕过 PermissionGate。
