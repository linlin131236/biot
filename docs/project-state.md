# Bolt/Biot Project State

## 当前稳定基线

- 已完成到：M170 E2E Autonomous Loop（本地验证通过，待 push）
- 当前分支：`main`
- 远端基线：`origin/main = 7f2567b docs: avoid self-referential M152 baseline hash`
- 本地 HEAD：M165-M170 收口提交（具体 hash 以 `git log -1` 为准）
- 本地状态：提交后预计 `main...origin/main [ahead 15]`
- 工作区状态：M165-M170 收口改动已验证并准备提交，`.claude/` 未跟踪且不提交。

## 已完成范围

- M153 Permission Center Live：权限中心 payload summary 脱敏。
- M154 Audit Timeline Live：审计时间线脱敏与 source 筛选。
- M155 Patch Preview Live：中文风险解释与 patch API 测试。
- M156 Approval Apply Desktop Flow：桌面端批准后应用闭环。
- M157 Safe Test Runner Live：白名单安全测试运行器 UI。
- M158 Task Result Summary：任务结果摘要结构化展示。
- M159 Researcher Execution Engine：研究者执行引擎。
- M160 Builder Execution Engine：构建者执行引擎。
- M161 Reviewer Execution Engine：严格 Reviewer Gate。
- M162 SkillLearner Auto Trigger：失败模式扫描与提案。
- M163 Orchestrator Core：五角色编排核心。
- M164 Sleep/Wake Mode：Agent 待机与唤醒状态。

## 当前收口范围

- M165 Gate Freeze：共享冻结状态，阻断自动继续与自主循环。
- M166 Tool Verification：只读工具链健康验证。
- M167 Self-Review Auto-Fix：低风险发现自动提案，不写文件。
- M168 Round Limit：自动循环最大 5 轮。
- M169 Auto Continue：自动继续状态控制，受 Gate Freeze 约束。
- M170 E2E Autonomous Loop：受限端到端诊断闭环。

## 已知风险

- M157 和 M161 各有一个 exec-plan-only 提交，随后由完整实现提交补齐；历史提交链可解释，但 review 时必须以最终 HEAD 文件状态为准。
- M153-M164 多个阶段由上一窗口完成，当前接手已验证关键文档链和 M165-M170 targeted tests，仍需在提交前跑完整质量门。
- `.claude/` 为外部工具状态目录，保持未跟踪、未提交。

## 硬规则

- 所有用户可见 UI 必须中文。
- 软件内不使用私人称呼，统一使用“用户 / 人工批准 / 用户确认”。
- 不自动 push、release、tag、delete。
- 不绕过 PermissionGate。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt/`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。

## 下一步

M165-M170 targeted tests、desktop tests、quality、docs、Chinese UI、diff check、安全扫描均已通过。下一步等待复审与 push 授权。
