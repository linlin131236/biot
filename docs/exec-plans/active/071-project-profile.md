# M71 Project Profile — 执行计划

## 目标
进入 V3 项目理解与长期记忆。建立项目画像，让新窗口能稳定理解项目：名称、路径、技术栈、关键命令、硬规则、里程碑状态、风险、常用文档入口。

## 参考资料
| # | 文件 | 采用原则 |
|---|------|---------|
| 1 | `20260628_上下文工程_Context_Engineering.md` | Context Lakehouse 原则：raw/source_refs 保留、清洗可复现、分析读清洗层、结论可追溯 |
| 2 | `20260628_Karpathy_LLM_Wiki_知识库新范式.md` | LLM Wiki 模式：结构化知识入口，而非全文加载 |
| 3 | `桌面AI编程Agent全流程架构对比.md` | 第 4 层上下文引擎：项目感知、文件索引、System Prompt 注入 |

## 范围
- 新增 `ProjectProfileService`：从 docs/git/filesystem 提取结构化项目画像
- Profile 字段：project_name, workspace_path, current_milestone, latest_head, origin_state, tech_stack, key_commands, hard_rules, important_docs, latest_review_gate, known_risks, source_refs
- 新增 API：`GET /project/profile`
- Context Lakehouse 原则贯彻：每个结论带 source_refs，文档缺失时中文降级

## 产出文件
- `services/agent-core/src/bolt_core/project_profile.py`
- `services/agent-core/src/bolt_core/project_profile_api.py`
- `services/agent-core/tests/test_project_profile.py`
- 修改 `app.py` 注册 router
- `docs/exec-plans/active/071-project-profile.md`（本文件）
- `docs/decisions/071-project-profile.md`
- `docs/phase-71-review-gate.md`

## 验收标准
- [x] 能返回项目名、workspace、当前 milestone
- [x] 能返回技术栈和关键命令
- [x] 能返回安全硬规则
- [x] 能返回最新 review gate
- [x] 每个重要结论带 source_refs
- [x] 文档缺失时中文降级，不崩
- [x] 不包含 secret
- [x] 不写 .bolt 或缓存
