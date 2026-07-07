# Phase 75 Review Gate — User Preference Memory

## 状态：✅ 通过

## 范围
- 新增 `UserPreferenceMemoryService`：12 条硬偏好，从 project-state + 用户指令固化
- 分类：language, address, workflow, safety, coding_style, product_direction
- 字段：preference_id, category, statement_cn, confidence, source_refs, can_apply_automatically, requires_confirmation
- 安全：secret 检测器（sk-/AKIA/PEM/token 模式）
- 冲突检查：auto_apply × requires_confirmation 矛盾诊断
- 新增 API：`GET /preferences`, `/preferences/summary`, `/preferences/{id}`, `/preferences/query/by-keyword`, `/preferences/check/conflicts`, `/preferences/check/secret`
- 修改 `app.py` 注册 router

## 测试
- targeted tests：42 passed（27 service + 15 API）
- 全量 backend：943 passed（901 → 943，零回归）

## 验收
- [x] 能返回爸爸明确偏好（全中文、称呼爸爸、不自动 push 等）
- [x] 每条偏好有 source_refs
- [x] 能识别硬偏好（全中文、称呼爸爸、不自动 push）
- [x] 不能记录 secret（secret 检测器验证）
- [x] 不能因为偏好绕过 PermissionGate（安全偏好无条件生效）
- [x] secret 检测器工作正常

## 安全边界
- [x] 纯静态数据，不存储用户输入
- [x] Secret 扫描通过
- [x] 安全偏好不可覆盖
- [x] 不暴露 renderer 危险对象

## 是否允许进入 M76
**✅ 是。M75 User Preference Memory 达标，允许进入 M76 Context Compaction。**
