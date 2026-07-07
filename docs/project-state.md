# Bolt Project State

## 当前稳定基线
- 已完成到：M61 Planner Task Graph
- 最新提交：（待提交）
- 远程状态：`main` 待 push（M58/M59/M60/M61 本地完成，准备 push）
- 最近稳定链路：... -> M55 Execution Audit Store Integrity Guard -> M56 Execution Evidence Redaction -> M57 Release Readiness Review Gate -> M58 Local Release Checklist -> M59 Rollback and Recovery Policy -> M60 Safety Baseline Dogfood -> M61 Planner Task Graph

## 当前进行中
- 当前阶段：M61 已完成，等待爸爸确认后 push
- 当前状态：M55-M61 全部实现并验证通过；M58-M61 未 push
- 当前结果：
  - V1 安全与发布底座（M55-M60）验收通过 ✅
  - V2 Agent 工作流核心启动（M61 Planner Task Graph）
  - M61：任务规划图数据模型 + 状态机 + 中文 UI；22 个 targeted tests
  - 591 backend + 195 frontend + 27 shared passed
  - 安全红线全部重新扫描通过
- 下一步：push 后等待爸爸指示；不进入 M62

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

## 当前风险
- M46 已验证不新增自动执行路径；后续 M47 若引入真实执行，必须重新建立 PermissionGate 边界。
- `queue approve` 只能代表队列项批准，不能等同于真实权限批准。
- `handoff` 只能记录下一步人工处理意图，不能直接调用 Harness、PermissionGate、Agent Loop 或 shell。
- 复审发现过的问题不能回退：切换闭环必须清空旧 queue item；handoff 终态不能被改写；本文件必须保持真实状态。

## 每个 milestone 必须产出
- `docs/exec-plans/active/0xx-*.md`
- `docs/decisions/0xx-*.md`
- `docs/phase-xx-review-gate.md`
- 更新本文件 `docs/project-state.md`
- 一个清晰 commit，push 只能在爸爸明确要求后执行

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
