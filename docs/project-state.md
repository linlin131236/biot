# Bolt Project State

## 当前稳定基线
- 已完成到：M82 Planner/Builder/Reviewer Split（V4 进行中）
- V3 项目理解与长期记忆（M71-M80）全部完成；V4 多 Agent 团队（M81-M90）进行中
- 远程状态：M67-M80 已 push，`main` 与 `origin/main` 已同步到 `db8194a`
- 远程状态：M67-M80 已 push，`main` 与 `origin/main` 已同步到 `db8194a`
- 最近稳定链路：M61 → M62 → M63 → M64 → M65 → M66 → M67 → M68 → M69 → M70（大复盘✅）→ M71 → M72 → M73 → M74 → M75 → M76 → M77 → M78 → M79 → M80（大复盘✅）→ M81

## 当前进行中
- 当前阶段：**M82 已完成，自动继续 M83**
- 当前状态：本地已 commit，未 push / 未 release / 未 tag / 未 delete
- 当前结果：
  - V2 Agent 工作流核心（M61-M70）beta 骨架达标
  - V3 项目理解与长期记忆（M71-M80）全部完成
  - V4 多 Agent 团队（M81-M90）进行中
  - M81：角色协议（58 tests，5 角色，6 端点）
  - M82：Planner/Builder/Reviewer 工作流（39 tests，9 状态，8 端点）
  - M71：项目画像（10 tests）
  - M72：代码地图索引（19 tests）
  - M73：决策记忆（39 tests，60+ 条决策记录）
  - M74：失败记忆（29 tests，P1/P2 + 已知风险）
  - M75：用户偏好记忆（42 tests，12 条硬偏好）
  - M76：上下文压缩（17 tests，组合各层，安全规则不截断）
  - M77：线程接手摘要（13 tests，Markdown/JSON，可复制给新 AI）
  - M78：记忆权限边界（29 tests，7 层权限分类 + secret 阻断）
  - M79：记忆搜索 UI（11 tests，中文只读面板）
  - M80：记忆层大复盘（11 tests，12 项检查全部通过）
  - V4 多 Agent 团队开局：M81 角色协议（58 tests，5 角色定义，6 只读端点）
	  - M81 验收：Planner 不能执行代码 ✅，Builder 不能 self-approve ✅，SkillLearner 不改业务代码 ✅
	  - M82：工作流状态机（39 tests，9 状态，8 端点，self-approval 硬阻断）
	  - 全量后端 1110 passed，前端 206 passed，desktop build 通过
  - 安全扫描全部干净
  - M80 结论：**V3 记忆层达标，允许进入 V4 多 Agent 团队**
	- 下一步：M82 已完成，自动继续 M83 Researcher Integration

## 已知风险
- M61 Task Graph 为纯内存模型（`PlannerTaskGraphService._graphs`），服务重启后图数据丢失。M62+ 引入状态机和持久化前需评估是否需要文件/数据库持久化。
- P3：此风险已记录，不作为 M61 阻断项。
- size check：部分文件超过 300 行（app.py、decision_memory.py、failure_memory_index.py、long_task_recovery_dogfood.py、memory_dogfood.py、project_profile.py），已有问题和新增文件混合，建议后续专项重构。

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
- M46 已验证不新增自动执行路径；后续 M47 若引入真实执行，必须重新建立 PermissionGate 边界。
- `queue approve` 只能代表队列项批准，不能等同于真实权限批准。
- `handoff` 只能记录下一步人工处理意图，不能直接调用 Harness、PermissionGate、Agent Loop 或 shell。
- 复审发现过的问题不能回退：切换闭环必须清空旧 queue item；handoff 终态不能被改写；本文件必须保持真实状态。

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
