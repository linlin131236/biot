# Decision 081 — Role Protocol

## 决策
定义 5 角色协议：Planner / Researcher / Builder / Reviewer / SkillLearner。

## 角色设计

| 角色 | 可执行代码 | 可写文件 | 可批准 | 核心约束 |
|------|:---:|:---:|:---:|------|
| Planner | ❌ | ❌ | ❌ | 只拆任务、不写代码 |
| Researcher | ❌ | ❌ | ❌ | 只读调研、限 2-4 资料、必带 source_refs |
| Builder | ✅ | ✅ | ❌ | 可写代码、不能 self-approve |
| Reviewer | ❌ | ❌ | ✅* | 只审不改、不能审查自己工作 |
| SkillLearner | ❌ | ❌ | ❌ | 只提案、不改业务代码、必须爸爸审批 |

*Reviewer 只能批准他人的工作。

## 理由
- Phase16 角色专精（Lesson 08）：每 Agent 一个角色，职责/边界/交互三要素
- Flock 权限模式：每个角色明确声明工具权限，Reviewer/Arbiter 只读
- Hermes SOUL.md 模式：身份 + 擅长 + 不擅长
- Claude Code：Plan 模式先出计划再执行

## 关键设计决策
1. **forbidden_actions 显式声明**：每个角色都有明确的禁止事项，比"允许"列表更重要
2. **output_requirements 强制 evidence/source_refs**：所有角色输出必须可追溯
3. **validate_transition 不自动执行**：只验证转换合法性，不触发实际操作
4. **Builder self-approval 阻断**：`assert_not_self_approval()` 硬阻断

## 权衡
- 简单 5 角色 vs 多层级：当前阶段 5 角色够用，层级架构（M82）再叠加
- 只读 API vs 可执行：当前阶段全部只读，不新增自动执行入口
- 硬编码角色 vs 可配置：硬编码保证一致性，未来可扩展

## 结果
- 5 角色定义完整
- 58 tests 通过
- 所有端点只读
- 中文 UI
- 不新增自动执行入口
