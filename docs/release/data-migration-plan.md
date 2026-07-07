# Beta Data Migration Plan

## 原则
- raw 原始数据只追加，不覆盖。
- staging 清洗过程必须可复现。
- clean 层用于默认分析查询。
- lineage 必须能从结论穿透回 raw/log/evidence。
- 所有迁移先 dry-run，再由爸爸人工 approval。
- rollback 必须能回到迁移前数据版本或人工备份点。

## 当前结论
M122 只检查迁移准备度，不执行迁移，不写入真实数据。
