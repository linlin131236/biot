# Phase 76 Review Gate — Context Compaction

## 状态：✅ 通过

## 范围
- 新增 `ContextCompactionService`：组合 M71-M75 记忆层生成压缩摘要
- 输出：objective, current_state, completed_milestones, active_constraints, relevant_decisions, known_failures, user_preferences, next_actions, source_refs
- 支持 max_items 截断，安全规则永不截断
- 支持 Markdown/JSON 双格式输出
- Token 估算功能
- 新增 API：`GET /context/compact`, `/context/compact/tokens`
- 修改 `app.py` 注册 router

## 测试
- targeted tests：17 passed (M76)
- 全量 backend：973 passed（943 → 973，零回归）

## 验收
- [x] 能生成 M67-M75 后的 compact summary
- [x] max_items 生效
- [x] 安全硬规则保留
- [x] source_refs 保留
- [x] 缺数据时中文降级（各组件独立容错）
- [x] 不调用 LLM
- [x] 中文输出

## 安全边界
- [x] 纯数据组合，无 LLM 调用
- [x] 安全规则永不截断
- [x] 不包含 secret

## 是否允许进入 M77
**✅ 是。M76 Context Compaction 达标，允许进入 M77 Thread Handoff Summary。**
