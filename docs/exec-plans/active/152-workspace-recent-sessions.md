# M152 Exec Plan - Workspace & Recent Sessions

## 目标

左侧项目、工作区路径、最近会话从假数据升级为真实数据源。用户切换工作区后 UI 即时更新，最近会话来自真实 backend 数据。

## 参考资料

本次 M152 开工前读取：
1. `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md` — 产品化流水线原则：用户第一屏应该是可用工作台，所有状态必须能解释下一步
2. `E:\BinCloud\知识库\03-知识\AI工程\20260628_上下文工程_Context_Engineering.md` — 上下文工程原则：原始数据只追加，清洗逻辑可复现
3. `services/agent-core/src/bolt_core/goal_persistence.py` — 现有目标持久化机制（goal_*.json）
4. `services/agent-core/src/bolt_core/desktop_settings.py` — M151 设置持久化服务（扩展 recent_workspaces）

## 范围

### 后端新增/修改
- `services/agent-core/src/bolt_core/desktop_settings.py`：
  - 新增 `recent_workspaces` 字段（list[str]，最多 10 个）
  - 添加工作区时自动去重并限制数量
- `services/agent-core/src/bolt_core/desktop_settings_api.py`：
  - `POST /desktop/settings/workspace-history` — 添加工作区到最近列表
- `services/agent-core/src/bolt_core/app.py`：注册新路由
- 新增 `services/agent-core/src/bolt_core/workspace_api.py`：
  - `GET /workspace/recent-sessions` — 返回当前工作区的最近目标/会话
    - 从 `.bolt/goals/goal_*.json` 读取
    - 按修改时间排序，最多返回 20 条
    - 每个会话显示：标题（objective）、时间、状态
  - `GET /workspace/status` — 返回当前工作区状态
    - `accessible`: bool
    - `path`: string
    - `goal_count`: int
- 在 `app.py` 注册 workspace router

### 前端更新
- `apps/desktop/src/harnessClient.ts`：
  - 新增 `addWorkspaceHistory`、`fetchRecentSessions`、`fetchWorkspaceStatus`
- `apps/desktop/src/workflowClient.ts`：
  - 新增 `addWorkspaceToHistory`、`loadRecentSessions`、`loadWorkspaceStatus`
- `apps/desktop/src/LiquidGlassWorkbench.tsx`：
  - `recentSessions` 从 API 加载，不再 hardcode
  - 切换工作区后自动添加到最近列表
  - 空状态中文展示
- `apps/desktop/src/App.tsx`：
  - `changeWorkspace` 后调用 `addWorkspaceToHistory`
  - 加载最近会话列表

### 安全要求
- 不扫描整个磁盘
- 只读取用户明确选择过的工作区的 `.bolt/goals/` 目录
- 不暴露敏感文件内容
- renderer 不暴露 `ipcRenderer`/`fs`/`shell`/`process`
- 不使用 `as any` / `unknown as`

## 验收

- 切换工作区后 UI 更新
- 最近会话来自真实 backend 数据（goal_*.json）
- 空状态中文清晰（未选择工作区、无最近会话、工作区不可访问）
- 不扫描整个磁盘
- renderer 安全扫描通过
