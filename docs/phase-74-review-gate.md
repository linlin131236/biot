# Phase 74 Review Gate — Failure Memory

## 状态：✅ 通过

## 范围
- 新增 `FailureMemoryIndexService`：从 review gates + project-state 构建只读失败索引
- 字段：failure_id, category, severity, milestone, symptom_cn, root_cause_cn, fix_summary_cn, verification, recurrence_risk, source_refs
- 分类对齐 M64（8 categories）
- 严重度：P1/P2（review gate 修复）、P3（project-state 风险）
- 查询能力：list, query by category, query by keyword, get detail, summary
- 新增 API：`GET /failures`, `/failures/summary`, `/failures/query/by-keyword`, `/failures/{failure_id}`
- 修改 `app.py` 注册 router

## 测试
- targeted tests：29 passed（15 service + 14 API）
- 全量 backend：901 passed（872 → 901，零回归）

## 验收
- [x] 能收录 M57/M60/M66/M67-M72 P1/P2
- [x] 中文失败解释和修复摘要
- [x] 每条失败记忆有 source_refs
- [x] 不包含 secret
- [x] 不触发自动修复（无 auto_fix_possible 暴露）
- [x] 不触发自动 retry
- [x] 不触发自动 approve

## 安全边界
- [x] 纯静态文件解析
- [x] 不执行代码
- [x] 不写入文件
- [x] 分类与 M64 对齐
- [x] 与 M65 对齐（不自动重试危险工具）

## 是否允许进入 M75
**✅ 是。M74 Failure Memory 达标，允许进入 M75 User Preference Memory。**
