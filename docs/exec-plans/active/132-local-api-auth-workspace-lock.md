# M132 Local API Auth + Workspace Lock 执行计划

## 背景

外部审计指出本地 Agent Core 运行在 `127.0.0.1`，但除系统回环地址外缺少调用门禁；同时桌面端选择的工作区没有被后端统一锁定为安全边界。经本地代码核验，这两项成立，优先作为 M132 修复。

审计中另外两项高优先级判断已核验：
- `needs_replan` 当前已在 `AgentLoop.run_loop()` 中继续下一轮，不再是未处理状态。
- `risk.py` 当前已有危险命令变体测试与正则拦截，不是单纯旧黑名单。

## 目标

1. Agent Core 支持本地访问令牌。
2. `/health` 保持公开，其他 API 在配置令牌后必须带 `Authorization: Bearer <token>`。
3. Electron 启动 Agent Core 时生成或继承本地令牌，并只通过环境变量传递，不进入命令行参数。
4. Renderer 通过受限 preload bridge 读取令牌，并自动附加到 API 请求。
5. 桌面启动时通过 `BOLT_WORKSPACE` 锁定后端工作区；显式锁定后，run workspace 只能位于锁定根目录内。
6. 保持历史测试中未显式工作区的 `create_app()` 兼容行为。

## 非目标

- 不引入远程账号体系、OAuth、云端登录。
- 不改变 PermissionGate 批准语义。
- 不重构所有 `_api.py` 路由。
- 不继续做 UI 外观迭代。

## 实施步骤

1. 新增本地 API auth 中间件和测试。
2. 扩展 Agent Core runtime，生成本地 token 并传给后端环境。
3. 扩展 preload bridge，只暴露 `agentCoreAuth()`，不暴露 `ipcRenderer`。
4. 新增 renderer authenticated fetcher，并接入 App 默认 fetcher。
5. 为 Harness 增加 optional locked workspace，显式锁定时拒绝越界 run workspace。
6. 跑 targeted tests、desktop tests、quality。

## 验收标准

- 缺少 token 访问受保护 API 返回 401 中文错误。
- 带正确 bearer token 访问受保护 API 成功。
- `/health` 不需要 token。
- Electron runtime 的 token 不出现在 args 中。
- locked workspace 拒绝锁外目录，允许锁内子目录。
- 桌面测试和后端相关测试通过。

