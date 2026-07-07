# Bolt Agent Product Roadmap M55-M125

## 产品目标
Bolt 的长期目标是做成接近 Claude/Codex 产品感的中文 Agent 桌面产品：能理解项目、能长期跑任务、能安全改代码、能审查自己、能恢复上下文、能用工具生态完成真实工作。

## 当前基线
- 已完成到：M54 Recovery Dogfood + Release Hardening。
- 当前能力：task closure、evidence verification、human approval queue、PermissionGate、execution handoff、audit persistence、recovery dogfood、timeline、diagnostics。
- 当前定位：已经有安全执行闭环骨架，但还不是完整产品。

## 节奏规则
- 每次推进 3 个 milestone：例如 M55-M57、M58-M60。
- 每 10 个 milestone 做一次大复盘：M60、M70、M80、M90、M100、M110、M120。
- 每个 milestone 必须产出 exec plan、decision、phase review gate、project-state 更新和一个清晰 commit。
- 每组结束后只在爸爸明确确认后 push。
- 不跳关：未完成当前授权范围，不进入下一组。
- 质量优先级：先不坏、不泄密、不盲飞，再扩智能和工具能力。

## 产品分层

### V1：安全与发布底座，M55-M60
目标：不坏、不泄密、不盲飞。

- M55 Execution Audit Store Integrity Guard：审计文件完整性和损坏诊断。
- M56 Execution Evidence Redaction：执行证据脱敏，防止 token/key/cert 泄露。
- M57 Release Readiness Review Gate：只读发布准备度检查。
- M58 Local Release Checklist：本地 release checklist，不自动 release。
- M59 Rollback and Recovery Policy：回滚/恢复策略。
- M60 Safety Baseline Dogfood：安全底座总 dogfood 和复盘。

验收：可以放心继续扩功能，发布前能看见阻断项，不会盲推。

### V2：Agent 工作流核心，M61-M70
目标：从“有闭环”变成“能自己做任务”。

- M61 Planner Task Graph
- M62 Execution State Machine
- M63 Tool Selection Policy
- M64 Failure Classification
- M65 Safe Retry Loop
- M66 Pause/Resume Long Task
- M67 Human Steering
- M68 Budget Controls
- M69 Long Task Recovery Dogfood
- M70 Agent Workflow Beta

验收：像早期 Codex agent，能跑长任务，但仍受 PermissionGate 和人工审查约束。

### V3：项目理解与长期记忆，M71-M80
目标：不再失忆，越来越懂项目。

- M71 Project Profile
- M72 Code Map Index
- M73 Decision Memory
- M74 Failure Memory
- M75 User Preference Memory
- M76 Context Compaction
- M77 Thread Handoff Summary
- M78 Memory Permission Boundary
- M79 Memory Search UI
- M80 Memory Dogfood

验收：新窗口接手更稳，能理解项目历史、失败模式和爸爸偏好。

### V4：多 Agent 团队，M81-M90
目标：Planner / Builder / Reviewer / Researcher 真正分工。

- M81 Role Protocol
- M82 Planner/Builder/Reviewer Split
- M83 Researcher Integration
- M84 Subtask Assignment
- M85 Reviewer Independent Gate
- M86 Conflict Resolution
- M87 Multi-Agent Status Board
- M88 SkillLearner Review Loop
- M89 Multi-Agent Recovery
- M90 Team Dogfood

验收：人物 AI 能分工跑完整任务，Reviewer 不再和 Builder 自我批准混在一起。

### V5：中文产品 UI/UX，M91-M100
目标：从工具变成可长期使用的中文桌面产品。

- M91 中文任务首页
- M92 权限中心
- M93 审计时间线视图
- M94 诊断中心
- M95 发布准备页
- M96 多任务队列
- M97 失败解释体验
- M98 会话恢复体验
- M99 设置/模型/工具面板
- M100 桌面 Beta Dogfood

验收：不只是 API 和测试，爸爸能在桌面里看清楚任务、权限、失败、恢复和下一步。

### V6：工具生态，M101-M112
目标：接近 Claude/Codex 的能力面。

- M101 Tool Registry
- M102 Tool Schema Validator
- M103 Browser Tool
- M104 File Edit Tool Hardening
- M105 Shell Policy Hardening
- M106 Docs/PDF Tool
- M107 Spreadsheet Tool
- M108 Web Research Connector
- M109 Plugin/Skill Registry
- M110 Tool Permission Tiers
- M111 Tool Eval Suite
- M112 Tool Ecosystem Dogfood

验收：工具能力有注册、权限、评估和 UI，不再靠散落的硬编码。

### V7：模型与智能策略，M113-M120
目标：更聪明、更稳、更省。

- M113 Model Routing
- M114 Context Budget Manager
- M115 Prompt Policy System
- M116 Agent Self-Review
- M117 Evaluation Harness
- M118 Benchmark Dashboard
- M119 Cost/Speed/Quality Profiles
- M120 Intelligence Dogfood

验收：不同任务能选择合适模型和策略，能评估质量，不靠感觉判断“聪明”。

### V8：产品级可靠性，M121-M125+
目标：接近真正产品发布底线。

- M121 Crash Recovery
- M122 Data Migration
- M123 Update/Rollback
- M124 Privacy/Security Audit
- M125 Public Beta Readiness

验收：能长期跑、可升级、可回滚、可审计，达到公开 beta 前的产品底线。

## 固定工作法
- 先写失败测试，再写最小实现。
- 每个 phase 都跑目标测试、相关全量测试、quality、docs、Chinese UI、安全扫描。
- review 发现 P1/P2 必须修复后再进入下一 milestone。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt/`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 不自动 push、release、tag、delete。

## 里程碑判断
- M60：安全底座可复盘。
- M70：最小可用 Agent workflow。
- M85：爸爸可长期自用。
- M100：桌面 Beta dogfood。
- M120：接近 Claude/Codex 产品感的智能策略审查。
- M125+：Public beta readiness。
