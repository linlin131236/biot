# Bolt Project State

## 当前稳定基线
- 已完成到：M73 Decision Memory
- M71-M73 已进入 V3 项目理解与长期记忆
- 全量测试：911 passed（872 backend + 27 shared + 12 desktop 未改动）
- 远程状态：M67-M72 已 push，M73 本地待 commit
- 最近稳定链路：M61 → M62 → M63 → M64 → M65 → M66 → M67 → M68 → M69 → M70（大复盘✅）→ M71 Project Profile → M72 Code Map Index → M73 Decision Memory

## 当前进行中
- 当前阶段：**M73 已完成，按文档规则自动继续 M74**
- 当前状态：本地 / 未 push / 未 release / 未 tag / 未 delete
- 当前结果：
  - V2 Agent 工作流核心（M61-M70）beta 骨架达标
  - V3 项目理解推进中（M71-M73）
  - M71：项目画像（project_name, workspace, milestone, tech_stack, hard_rules, risks, source_refs；10 tests）
  - M72：代码地图索引（静态解析，4 个 scope 目录，按关键词/分类查询，19 tests）
  - M73：决策记忆（从 docs/decisions/*.md 解析 60+ 条决策记录；39 tests）
  - 全量后端 872 passed，前端 195 passed，desktop build 通过
  - 安全扫描全部干净
- 下一步：进入 M74 Failure Memory

## 已知风险
- M61 Task Graph 为纯内存模型（`PlannerTaskGraphService._graphs`），服务重启后图数据丢失。M62+ 引入状态机和持久化前需评估是否需要文件/数据库持久化。
- P3：此风险已记录，不作为 M61 阻断项。

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
