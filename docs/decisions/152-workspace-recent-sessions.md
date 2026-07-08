# M152 Decision - Workspace & Recent Sessions

## 决策

M152 将左侧工作区和最近会话从假数据升级为真实数据源，基于现有 goal 持久化和 M151 设置服务扩展。

## 背景

M151 已完成设置持久化，但工作区选择和最近会话仍然是硬编码 mock 数据。用户切换工作区后，左侧"最近会话"不会变化，也无法追溯历史工作区。

## 方案选择

| 方案 | 描述 | 决策 |
|------|------|------|
| A | 全新 SQLite 存储会话历史 | ❌ 过重，已有 goal_*.json 和 conversations.db |
| B | 纯 localStorage 存储最近会话 | ❌ 后端无法共享，多设备不同步 |
| C | 扩展 desktop_settings.json + 新增 workspace API 读取 goals | ✅ 轻量、复用现有数据源 |

### C 方案细节
- **recent_workspaces**：扩展 `desktop_settings.json`，添加 `recent_workspaces` 字段（list[str]，最多 10 个，去重）
- **recent_sessions**：新增 `GET /workspace/recent-sessions`，读取当前工作区 `.bolt/goals/goal_*.json`，按修改时间排序
- **workspace_status**：新增 `GET /workspace/status`，检查工作区是否可访问
- 前端切换工作区后自动添加到最近列表
- 空状态中文展示

## 风险

- `.bolt/goals/` 目录可能不存在于新工作区
- goal 文件可能损坏，需要跳过而非崩溃
- 最近工作区列表需要限制数量避免 localStorage 溢出
- 工作区不可访问时需要优雅降级
