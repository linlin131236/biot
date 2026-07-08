# M132 Decision: 本地 API 令牌与工作区硬边界

## 决策

采用“本地随机令牌 + 显式工作区锁”的最小安全闭环。

## 原因

桌面应用虽然把 Agent Core 绑定到 `127.0.0.1`，但本机其他进程仍可直接请求本地端口。Biot 的能力包含读取文件、申请写入、审批后写入和执行命令，因此只依赖回环地址不够。

同时，用户在桌面端选择的工作区应当成为后端所有 run 的边界。否则 renderer 或其他本地调用者可以传入另一个工作区路径，削弱 PathGuard/PermissionGate 的语义。

## 方案

- 后端新增 `install_local_api_auth()`：
  - 配置 token 后，除 `/health`、文档页和 `OPTIONS` 外全部校验 `Authorization: Bearer <token>`。
  - 未配置 token 时保持测试/开发兼容。
- Electron runtime：
  - 使用 `BOLT_AGENT_CORE_TOKEN` 或随机 UUID 作为本地 token。
  - token 只放进环境变量，不放进命令行参数。
  - 设置 `BOLT_WORKSPACE` 作为后端显式锁定根。
- Preload：
  - 只新增 `window.bolt.agentCoreAuth()`。
  - 不暴露 `ipcRenderer` 或通用 invoke。
- Harness：
  - 新增 optional `locked_workspace`。
  - 启用锁定后，run workspace 必须位于锁定根目录内。

## 取舍

- 不做用户登录：本次防的是本机端口被其他进程随意调用，不是云端多用户鉴权。
- 不默认锁死所有 `create_app()`：大量后端测试和服务端集成仍依赖临时工作区。只有 `project_dir` 或 `BOLT_WORKSPACE` 明确给出时启用锁。
- 不把 token 写入 localStorage：避免持久化敏感材料。

## 风险

- dev server 手动访问 API 时需要显式配置/获取 token。
- 后续若增加多窗口/多工作区，需要把 workspace lock 提升为受控会话模型。

