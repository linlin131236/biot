# Phase 73 Review Gate — Decision Memory

## 状态：✅ 通过

## 范围
- 新增 `DecisionMemoryService`：从 `docs/decisions/*.md` 构建只读决策索引
- 解析 60+ 条历史决策记录
- 字段：decision_id, milestone, title, summary_cn, rationale, tradeoffs, outcome, source_refs
- 查询能力：list, query by milestone, query by keyword, get detail, summary
- 新增 API：`GET /decisions`, `/decisions/summary`, `/decisions/query/by-keyword`, `/decisions/{decision_id}`
- 修改 `app.py` 注册 router

## 测试
- targeted tests：39 passed（24 service + 15 API）
- 全量 backend：872 passed（833 → 872，零回归）
- shared tests：待跑
- desktop tests：未改动，无需跑

## 验收
- [x] 能列出 M55-M72 已有 decision（60+ 条）
- [x] 能查询 M70/M71/M72 决策
- [x] 每条 decision 有 source_refs
- [x] 缺失/格式异常文档时中文降级，不崩
- [x] 不读取 secret、证书材料
- [x] 不新增自动执行入口（API 无 POST/PUT/DELETE）
- [x] 不新增自动 approve
- [x] 不绕过 PermissionGate

## 安全边界
- [x] 纯静态文件解析，无 LLM 调用
- [x] 不执行代码
- [x] 不写入文件
- [x] secret 扫描通过
- [x] 不暴露 renderer 危险对象

## 是否允许进入 M74
**✅ 是。M73 Decision Memory 达标，允许进入 M74 Failure Memory。**
