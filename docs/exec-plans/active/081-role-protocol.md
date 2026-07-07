# M81 Exec Plan — Role Protocol

## 目标
定义多 Agent 团队角色协议，明确 Planner / Builder / Reviewer / Researcher / SkillLearner 的职责、输入、输出、禁止事项和交接格式。

## 参考资料
| 文件 | 采用原则 |
|------|---------|
| `AI工程-Phase16-多Agent与群体-深度笔记.md` | 角色专精（Lesson 08）：每 Agent 一个角色，职责/边界/交互三要素；禁止越界 |
| `Flock架构分析——AI开发团队流水线设计.md` | 角色权限声明（YAML+tools）、Arbiter 仲裁、Reviewer 只读、对抗性评审 |
| `Hermes多Agent团队Profile搭建实战.md` | SOUL.md 身份+擅长+不擅长模式；AGENTS.md 共享背景 |
| `docs/桌面AI编程Agent全流程架构对比.md` | Claude Code Plan 模式 + 子代理分发；第6层任务编排定位 |

## 设计决策

### 5 角色定义
| 角色 | 职责 | 可执行代码 | 可写文件 | 可批准 |
|------|------|:---:|:---:|:---:|
| Planner | 拆任务、定义验收标准、分配角色 | ❌ | ❌ | ❌ |
| Researcher | 只读调研、提炼资料、输出 source_refs | ❌ | ❌ | ❌ |
| Builder | 实现代码、写测试、提交变更 | ✅ | ✅ | ❌ |
| Reviewer | 独立审查、找 P1/P2、不能实现自己的 review 发现 | ❌ | ❌ | ✅* |
| SkillLearner | 总结流程缺陷、提出技能/流程改进建议 | ❌ | ❌ | ❌ |

*Reviewer 只能批准其他人的工作，不能批准自己的工作。

### 核心规则
- 每个角色必须有 forbidden_actions 列表
- 每个角色输出必须有 evidence_refs 或 source_refs
- Builder 不能 self-approve
- Reviewer 不能和 Builder 同一角色上下文
- Planner/Researcher/SkillLearner 只读，不能写代码

### 交接格式
角色间交接使用结构化 HandoffPackage：
- from_role / to_role
- task_id
- summary_cn
- evidence_refs
- source_refs
- warnings（已知风险）

## 产出文件
- `services/agent-core/src/bolt_core/role_protocol.py` — RoleProtocol 数据模型 + RoleProtocolService
- `services/agent-core/src/bolt_core/role_protocol_api.py` — FastAPI router（只读）
- `services/agent-core/tests/test_role_protocol.py` — 单元测试
- `services/agent-core/tests/test_role_protocol_api.py` — API 测试
- 修改 `app.py` 注册 router
- `docs/decisions/081-role-protocol.md`
- `docs/phase-81-review-gate.md`

## API 端点（只读）
- `GET /roles` — 列出 5 个角色
- `GET /roles/{role_id}` — 角色详情（中文）
- `POST /roles/validate-output` — 验证角色输出
- `GET /roles/{role_id}/boundary` — 角色边界说明（中文）
- `POST /roles/validate-transition` — 验证角色转换是否合法
- `GET /roles/handoff-format` — 交接格式说明

## 验收标准
1. 能列出 5 个角色
2. 能验证 Planner 不能执行代码
3. 能验证 Reviewer 不能 approve 自己的 Builder 输出
4. 能验证 SkillLearner 不能改业务代码
5. 所有用户可见文案中文
6. 不新增自动执行入口
7. 所有端点只读
