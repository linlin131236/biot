# M59 执行计划：Rollback and Recovery Policy

## 目标
建立故障恢复策略，只读输出人工恢复步骤，不自动执行回滚。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`：安全 checklist 模式
- M55-M58 安全底座：审计完整性、证据脱敏、发布准备度、本地发布清单

## 实现方案

### 后端
- `bolt_core/recovery_policy.py`：RecoveryPolicyService
  - list_scenarios() 返回 10 个恢复场景
  - 5 个分类：审计完整性、发布失败、权限误操作、任务中断、数据损坏
  - 每个场景包含：标题、严重度、描述、恢复步骤、警告
  - 不执行任何 git 操作、不调用危险命令
- `bolt_core/recovery_policy_api.py`：GET /recovery-policy (只读)

### 前端
- RecoveryPanel 组件：可折叠详情展示
- 全中文 UI

## 验收标准
- [x] 10 个恢复场景覆盖审计/发布/权限/中断/数据
- [x] 每个场景有恢复步骤和警告
- [x] 明确标注"需人工介入"vs"可自动恢复"
- [x] API 只读
- [x] 无自动执行
- [x] 14 个 targeted tests
- [x] 全量验证通过
