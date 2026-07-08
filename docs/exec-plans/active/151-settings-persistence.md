# M151 Exec Plan - 真实设置持久化

## 目标

设置中心从静态展示升级为真实读写：主题切换重启后恢复、模型提供方状态可保存/读取、API 密钥不泄露、语言状态真实展示、默认工作区可读取。

## 参考资料

本次 M151 开工前读取：
1. `services/agent-core/src/bolt_core/model_settings.py` — 现有模型配置内存存储，需要升级为持久化
2. `services/agent-core/src/bolt_core/settings_tools_api.py` — M99 设置工具 API 模式参考
3. `services/agent-core/src/bolt_core/permission_center_api.py` — 权限中心 API 模式参考
4. `apps/desktop/src/desktopSession.ts` — 现有桌面 session 持久化模式（localStorage）

## 范围

### 后端新增
- `services/agent-core/src/bolt_core/desktop_settings.py`：设置持久化服务
  - 读取/写入 `.bolt/desktop-settings.json`
  - 读取/写入 `.bolt/desktop-api-key`（文件权限 600）
  - API key 只存状态（has_api_key），不回显明文
  - 默认值：theme=dark, language=zh-CN, default_workspace=""
- `services/agent-core/src/bolt_core/desktop_settings_api.py`：FastAPI 路由
  - `GET /desktop/settings` — 返回设置状态（不含明文 key）
  - `POST /desktop/settings` — 保存设置（不含明文 key）
  - `POST /desktop/settings/api-key` — 保存 API key（独立端点，脱敏日志）
  - `DELETE /desktop/settings/api-key` — 清除 API key
- 在 `app.py` 注册路由

### 前端更新
- `apps/desktop/src/LiquidGlassSettings.tsx`：
  - 顶部标签从静态改为真实状态（深色/浅色、简体中文、模型已配置/未配置）
  - 主题切换按钮调用 `saveDesktopSettings` API，不再只是本地 state
  - 设置页加载时从 API 读取状态
- `apps/desktop/src/LiquidGlassWorkbench.tsx`：
  - theme state 从 API 初始化，不再硬编码 'dark'
  - 设置保存结果中文提示
- `apps/desktop/src/harnessClient.ts`：
  - 新增 `fetchDesktopSettings`、`saveDesktopSettings`、`saveDesktopApiKey`、`deleteDesktopApiKey`
- `apps/desktop/src/workflowClient.ts`：
  - 新增 `loadDesktopSettings`、`storeDesktopSettings`、`storeDesktopApiKey`、`removeDesktopApiKey`
- `apps/desktop/src/App.tsx`：
  - 初始化时加载桌面设置，同步 theme
  - 保存设置结果中文提示

### 安全要求
- 不保存明文 API key 到 repo
- API key 存储位置在 `.bolt/` 目录（已 gitignore）
- API key 文件权限 600
- API 返回只包含 `has_api_key: true/false`
- renderer 不暴露 `ipcRenderer`/`fs`/`shell`/`process`
- 不使用 `as any` / `unknown as`

## 验收

- 切换主题后重启应用，主题恢复
- 保存模型配置后重启，配置恢复
- API key 不回显在 UI 或日志
- 设置保存结果中文提示
- renderer 安全扫描通过
- targeted tests 通过
