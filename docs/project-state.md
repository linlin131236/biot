# Bolt Project State

## 当前稳定基线
- 已完成到：**M100 桌面 Beta Dogfood（V5 终点，等待爸爸复审）**
- V5 中文产品 UI/UX（M91-M100）全部完成
- 全量测试：1214 backend + 27 shared + 261 desktop = **1502 passed**
- 远程状态：未 push / 未 release / 未 tag / 未 delete
- 最近稳定链路：M61→M90→M91→M92→M93-M95→M96-M99→M100（大复盘✅）

## 当前进行中
- 当前阶段：**M100 已完成，按文档规则停止，未进入 M101**
- V5 合计：**+80 tests，+9 后端服务，+9 桌面面板**
- 当前状态：M91-M100 未 push / 未 release / 未 tag / 未 delete / 未进入 M101
- V5 各 milestone 结果：
  - M91：中文任务首页（23 tests）
  - M92：权限中心（22 tests）
  - M93：审计时间线视图（6 tests）
  - M94：诊断中心（6 tests）
  - M95：发布准备页（7 tests）
  - M96：多任务队列（3 tests）
  - M97：失败解释体验（3 tests）
  - M98：会话恢复体验（3 tests）
  - M99：设置/模型/工具面板（3 tests）
  - M100：桌面 Beta Dogfood（4 tests）
- Desktop build：通过
- 安全扫描：全部干净
- M100 结论：**V5 中文产品 UI/UX 达标，13/13 检查项通过。等待爸爸复审后授权 push 和/或进入 M101。**
- 下一步：⛔ 停止，等待爸爸复审

## 已知风险
- 预存：GoalConsole.test.tsx 1 个测试失败（act() wrapping），非本次引入
- size check：部分文件超过 300 行，建议后续专项重构
- backend API tests 受 pydantic 环境问题影响无法运行（预存问题）
- `.claude/` 未跟踪、未提交，按规则保持

## 已知风险
- M61 Task Graph 为纯内存模型，服务重启后数据丢失。M62+ 引入状态机和持久化前需评估。
- M81-M89 工作流状态机均为纯内存（`_workflows: dict`），重启后丢失。M89 有恢复策略但未持久化。
- SkillLearner 需接入真实 M64 FailureClassifier 数据进行模式检测（当前手动录入）。
- size check：部分文件超过 300 行（app.py、decision_memory.py、failure_memory_index.py、multi_agent_workflow.py、role_protocol.py、project_profile.py、memory_dogfood.py、long_task_recovery_dogfood.py），建议后续专项重构。
- P3：以上风险已记录，不作为当前阶段阻断项。

## 长期硬规则
- 所有用户可见 UI 必须中文。
- 不自动 push、release、tag、delete。
- 不自动执行 verification command。
- 不自动批准 PermissionGate。
- 不绕过 PermissionGate。
- 不提交生成物、缓存、虚拟环境或证书材料。
- 不进入未授权 milestone。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 代码文件尽量保持在 300 行以内，接近上限时拆到聚焦组件或服务。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。

## 当前风险
- M46 已验证不新增自动执行路径；后续若引入真实执行，必须重新建立 PermissionGate 边界。
- `queue approve` 只能代表队列项批准，不能等同于真实权限批准。
- `handoff` 只能记录下一步人工处理意图，不能直接调用 Harness、PermissionGate、Agent Loop 或 shell。
- 复审发现过的问题不能回退：切换闭环必须清空旧 queue item；handoff 终态不能被改写；本文件必须保持真实状态。
- `.claude/` 未跟踪、未提交，按规则保持。
- `docs/references/anthropic-jlens-global-workspace-2026.md` 为长期安全研究参考文档（已纳入知识索引 M113-M120、M124+ 区段），已提交。

## 新窗口接手指令
```text
工作目录：D:\Bolt\Bolt

请先恢复项目上下文，不要改文件：
1. 读取 docs/project-state.md
2. 读取最新 docs/phase-*-review-gate.md
3. 运行 git status --short --branch
4. 运行 git log --oneline -6 --decorate
5. 汇报当前稳定基线、正在进行的 milestone、未提交改动和下一步
6. 等我确认后再开始实现或审查

硬规则：
- 全中文 UI
- 不自动 push
- 不进入未授权 milestone
- 不绕过 PermissionGate
- 不自动执行危险命令
- 不提交生成物
- 每完成一个 phase 自动继续，除非验证失败、出现 blocker、或需要扩大范围
```
