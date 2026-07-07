# M58 执行计划：Local Release Checklist

## 目标
建立本地 release checklist，只读检查，不自动 release。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`：安全加固 checklist 模式
- M57 Release Readiness Review Gate：只读检查模式复用

## 实现方案

### 后端
- `bolt_core/local_release_checklist.py`：LocalReleaseChecklistService
  - checklist() 返回结构化清单
  - 8 个检查项：审计完整性、证据安全、代码状态、分支同步、文档一致性、审查门、发布确认
  - 不执行任何 git 写操作、不调用 release/tag/delete
- `bolt_core/local_release_checklist_api.py`：GET /local-release-checklist (只读)

### 共享类型
- `protocol-release.ts`：ReleaseReadiness、LocalReleaseChecklist 等类型

### 前端
- ExecutionHandoffPanel 新增 Checklist 组件
- 全中文 UI，表格展示分类、检查项、状态、详情、建议
- 不提供"点击发布"入口

## 验收标准
- [x] 后端 service + API 只读
- [x] UI 全中文
- [x] 无自动发布入口
- [x] 测试覆盖 clean、缺项、阻断项、只读行为
- [x] 14 个 targeted tests
- [x] 全量验证通过
