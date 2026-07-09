# Bolt/Biot Project State

## 当前稳定基线

- 当前分支：`main`
- 远端基线：`origin/main = 7f2567b docs: avoid self-referential M152 baseline hash`
- 已完成到：M170 E2E Autonomous Loop，本轮正在收口 M165-M170 复审修复
- 本地状态：本轮修复提交后预计 `main...origin/main [ahead 16]`
- 工作区约定：`.claude/` 为外部工具状态目录，保持未跟踪、未提交

## 已完成范围

- M153 Permission Center Live：权限中心真实接入与 payload summary 脱敏
- M154 Audit Timeline Live：审计时间线真实接入、脱敏与 source 筛选
- M155 Patch Preview Live：中文风险解释与 patch API 测试
- M156 Approval Apply Desktop Flow：桌面端批准后应用闭环
- M157 Safe Test Runner Live：白名单安全测试运行器 UI
- M158 Task Result Summary：任务结果摘要结构化展示
- M159 Researcher Execution Engine：研究者执行引擎
- M160 Builder Execution Engine：构建者执行引擎
- M161 Reviewer Execution Engine：严格 Reviewer Gate
- M162 SkillLearner Auto Trigger：失败模式扫描与提案
- M163 Orchestrator Core：五角色编排核心
- M164 Sleep/Wake Mode：Agent 待机与唤醒状态
- M165 Gate Freeze：共享冻结状态，阻断自动继续与自主循环
- M166 Tool Verification：只读工具链健康验证
- M167 Self-Review Auto-Fix：低风险发现自动提案，不直接写文件
- M168 Round Limit：自动循环最大 5 轮
- M169 Auto Continue：自动继续状态控制，受 Gate Freeze 约束
- M170 E2E Autonomous Loop：受限端到端诊断闭环

## 本轮复审修复

- P1：旧 `/permissions/{request_id}/approve` 批准入口补上 Gate Freeze 检查，冻结后返回 423，不再绕过冻结门。
- P1：M165-M170 新增桌面面板统一使用父级注入的认证 `fetcher`，不再直接使用全局 `window.fetch`。
- P1：主题保存改为通过 `storeDesktopSettings(session.coreUrl, ..., fetcher)` 写入，修复运行时未定义函数问题。
- P2：`/orchestrator/auto-continue` 与 `/orchestrator/autonomous-loop` 对非法 `max_rounds` 返回 400。
- P2：M170 自主循环改为调用 `OrchestratorEngine`，不再返回硬编码假 trace。

## 已知风险

- M157 和 M161 各有一个 exec-plan-only 历史提交，后续完整实现提交已补齐；复审时必须以最终 HEAD 文件状态为准。
- M153-M170 多个阶段由不同窗口完成，继续推进前必须坚持 targeted tests、full tests、quality、docs、Chinese UI、diff check 和安全扫描。
- `.claude/` 保持未跟踪、未提交。

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

完成本轮修复验证后，等待复审与 push 授权。若继续产品化，下一批应回到桌面端真实体验、打包 smoke 和可用性验证，而不是继续扩大自主 Loop 权限。
