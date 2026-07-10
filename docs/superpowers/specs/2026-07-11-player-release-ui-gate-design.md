# Bolt 玩家发布 UI 门禁：Core URL 移除 + Desktop 全绿

- 日期：2026-07-11
- 状态：待用户书面审阅
- 分支：`feat/safe-controlled-beta`
- 前置：P0 本地安全纵向切片技术验收完成
- 范围：Renderer Core URL 语义清除、只读 Agent Core 状态、path-only client、Desktop 全量测试全绿
- 发布状态：本切片完成后仍禁止玩家内测与公开 Beta，直到独立 Release Evidence 切片完成

## 1. 目标

关闭玩家发布前的 **可编辑 Core URL UI 门禁**，并让 `@bolt/desktop` 全量测试全绿。

用户看到的是：

```text
本地 Agent Core · 由 Bolt 自动管理
```

用户看不到、也不能配置任何 Core URL。真实 endpoint 与 Bearer 继续只存在于 Electron Main 的 verified generation。

## 2. 完成定义

1. Renderer 不再持有、展示、持久化可配置 Core URL。
2. 设置中心只读展示：`本地 Agent Core · 由 Bolt 自动管理`。
3. 工作台只展示健康状态（`本地` / `离线`），不出现地址输入框。
4. client 调用改为 path-only；真实 endpoint 只由 Main verified generation 决定。
5. Desktop 全量 `vitest` 全绿；P0 focused suite 不回归。
6. architecture gate 与 desktop build 通过。

## 3. 明确不做

- 不修改已验收的 P0 安全实现：credential gate、generation secrets、atomic write、Windows Credential Manager。
- 不做 Windows 打包、签名、升级、崩溃反馈、Release Evidence。
- 不恢复旧面板布局去迁就过期测试。
- 不恢复生产 `fetch` fallback。
- 不重新引入 `window.bolt.agentCoreEndpoint`。

## 4. 当前问题

P0 已封死网络边界，但产品层仍残留误导语义：

1. `DesktopSession.coreUrl` 与 `DEFAULT_CORE_URL` 仍存在。
2. `App`、`LiquidGlassWorkbench`、`panelsApi`、`harnessClient`、`workflowClient` 仍把 `baseUrl`/`coreUrl` 当调用参数传递。
3. 错误文案仍可能引导用户“检查核心服务地址”。
4. 旧 UI/dogfood 测试仍断言已移除控件（如 `核心服务地址`、旧按钮文案），导致 Desktop 全量约 37 红。
5. 即使 URL 不决定真实网络目标，保留可配置地址语义仍阻塞玩家发布门禁。

## 5. 架构

### 5.1 目标数据流

```text
UI / panelsApi / workflow
  -> harnessClient / coreClient (path-only)
  -> AgentCoreTransport(inputPath, init)
  -> preload agentCoreRequest DTO
  -> Main verified generation endpoint + Bearer
  -> loopback Agent Core
```

### 5.2 Session 与配置

`DesktopSession` 删除 `coreUrl`：

```ts
export interface DesktopSession {
  completed: boolean;
  workspacePath: string;
  lastRunId: string | null;
}
```

规则：

1. 删除 `DEFAULT_CORE_URL`。
2. `loadDesktopSession` 读取旧 JSON 时忽略历史 `coreUrl`。
3. `saveDesktopSession` 永不写入 `coreUrl`。
4. 首次运行向导只收集 workspace；不收集 Core URL。

### 5.3 Client 签名

`coreClient`、`harnessClient`、`workflowClient`、`panelsApi` 及相关 UI props：

- 删除 `baseUrl` / `coreUrl` 参数。
- 调用方只提供 path、body、method 所需业务参数。
- 内部拼接相对 path，例如 `/harness/runs`、`/health`、`/desktop/settings`。

示例：

```ts
// before
fetchCoreHealth(baseUrl, fetcher)

// after
fetchCoreHealth(fetcher)
// transport 请求 "/health"
```

### 5.4 Transport 输入规则

1. 生产 transport 输入优先为相对 path（必须以 `/` 开头）。
2. 兼容迁移期内，若测试或遗留代码传入 absolute URL，transport/adapter 只提取 path + query。
3. host / port / scheme / userinfo / fragment 永不决定真实网络目标。
4. Main 始终使用当前 `VERIFIED` generation 的 `127.0.0.1:<actual-port>`。
5. 测试通过显式注入 fetcher/transport；不为测试保留生产逃生路径。

## 6. UI 设计

### 6.1 设置中心

在设置中心“常规/连接”区域固定只读展示：

- 文案：`本地 Agent Core · 由 Bolt 自动管理`
- 健康：`本地` / `离线`（来自 core health）
- 不展示 URL、端口、token、endpoint

### 6.2 工作台

- 状态栏继续使用现有 `coreStatus` 语义：`本地` / `离线`
- 不出现地址输入框
- 不出现“核心服务地址”标签

### 6.3 首次运行向导

- 保持现有说明：核心服务由桌面端安全管理
- 不增加可编辑 Core URL

### 6.4 错误文案

旧：

```text
无法连接 Agent Core。请确认服务已启动并检查核心服务地址。
```

新：

```text
无法连接本地 Agent Core。请确认 Bolt 桌面端已启动核心服务。
```

所有引导用户修改 Core URL 的文案删除。

## 7. 测试策略

### 7.1 生产代码优先

按 TDD 顺序：

1. session 删除 `coreUrl` 的 RED/GREEN
2. path-only client 的 RED/GREEN
3. 设置中心只读状态文案的 RED/GREEN
4. 错误文案替换的 RED/GREEN

### 7.2 Desktop 全量修绿

按当前 LiquidGlass 产品壳重写断言，不迁就旧 UI：

重点文件：

- `apps/desktop/src/App.test.tsx`
- `apps/desktop/src/uiWorkflowDogfood.test.tsx`
- `apps/desktop/src/AutoContinuePanel.test.tsx`
- `apps/desktop/src/SkillLearnerPanel.test.tsx`
- `apps/desktop/src/taskClosureDogfood.test.tsx`
- `apps/desktop/src/taskClosureAssessmentDogfood.test.tsx`
- `apps/desktop/src/desktopSession.test.ts`
- 所有因删除 `baseUrl`/`coreUrl` 参数而编译或断言失败的 client/panel 测试

规则：

1. 删除对已移除控件的断言（如 `核心服务地址` input）。
2. 保留真实业务意图：创建任务、权限、工作区选择、健康状态、模型设置不落明文密钥。
3. 测试注入 fetcher 时使用相对 path 期望，例如 `/health`，不再期望 `http://core/health` 这类假绝对地址。

### 7.3 验收命令

```powershell
pnpm.cmd --filter @bolt/desktop exec vitest run src/desktopSession.test.ts src/agentCoreAuth.test.ts src/harnessClient.test.ts src/App.test.tsx src/uiWorkflowDogfood.test.tsx

pnpm.cmd --filter @bolt/desktop exec vitest run src/desktopSession.test.ts src/harnessClient.test.ts src/LiquidGlassSettingsCredential.test.tsx src/agentCoreAuth.test.ts electron/agentCoreAuth.test.ts electron/preloadBridge.test.ts electron/mainSecurity.test.ts electron/agentCoreRuntime.test.ts electron/agentCoreReadiness.test.ts electron/agentCoreIpc.test.ts electron/desktopStartup.test.ts electron/electronBridge.integration.test.ts

pnpm.cmd --filter @bolt/desktop test -- --run
pnpm.cmd --filter @bolt/desktop build
node scripts/check-architecture.mjs
git diff --check
```

## 8. 文件影响面（预期）

### 生产代码

- `apps/desktop/src/desktopSession.ts`
- `apps/desktop/src/App.tsx`
- `apps/desktop/src/agentCoreAuth.ts`（如需 path 规范化）
- `apps/desktop/src/coreClient.ts`
- `apps/desktop/src/harnessClient.ts`
- `apps/desktop/src/harnessClientAutonomy.ts`
- `apps/desktop/src/workflowClient.ts`
- `apps/desktop/src/panelsApi.ts`
- `apps/desktop/src/LiquidGlassTypes.ts`
- `apps/desktop/src/LiquidGlassWorkbench.tsx`
- `apps/desktop/src/LiquidGlassSettings.tsx` / `LiquidGlassSettingsData.tsx`
- 各 Panel 中仍接收 `baseUrl` 的调用点

### 测试代码

- `desktopSession.test.ts`
- `App.test.tsx`
- `uiWorkflowDogfood.test.tsx`
- client/panel/dogfood 相关失败测试
- 保持 P0 electron 安全测试不回归

## 9. 风险与非回归

1. **签名面大**：删除 `baseUrl` 会波及大量 panel props；必须用编译错误和 focused tests 驱动，避免漏改。
2. **假 absolute URL 测试债务**：旧测试大量写入 `coreUrl: 'http://core'`；必须改为 path-only 期望。
3. **不碰 P0**：不得为修 UI 测试而削弱 IPC transport、generation revoke、credential gate。
4. **不宣称可发布**：本切片只关闭 UI 门禁；玩家内测仍禁止。

## 10. 发布决策

| 场景 | 本切片完成后 |
|------|----------------|
| 本地开发 | 允许 |
| 团队内部验证 | 允许 |
| 玩家小范围内测 | 仍禁止 |
| 公开 Beta | 仍禁止 |

下一步独立切片：Windows 打包、签名、升级、崩溃反馈、完整 Release Evidence。

## 11. 实施顺序

1. Session 去 `coreUrl`
2. path-only client 改造
3. UI 只读状态与错误文案
4. 对齐现 UI 修齐 Desktop 全量测试
5. 复跑 P0 focused + architecture + build
6. 交付时明确：UI 门禁关闭，玩家发布仍阻塞
