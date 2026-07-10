# Bolt P0 本地安全边界设计

- 日期：2026-07-10
- 状态：待书面复审
- 分支：`feat/safe-controlled-beta`
- 范围：Renderer Transport、Agent Core 启动身份、Windows 凭据、旧明文密钥迁移
- 发布状态：P0 安全切片未完成；禁止玩家内测和公开发布

## 1. 决策摘要

本轮停止原有零散 Task 1–4，改为一个不可拆分验收的 P0 安全纵向切片。四项能力必须同时通过，才可将本切片标记为完成：

1. Renderer 到 Agent Core 的所有生产请求只经过唯一 IPC transport。
2. Electron Main 为 child 提供本 generation 的 Bearer Token，但只有在 readiness proof 和 strict health 验证成功后，Main 才在 HTTP 请求中使用它；预占端口服务永远收不到 Bearer。
3. Windows API Key 只进入 Windows Credential Manager；DPAPI 文件存储不接入生产。
4. 旧 `.bolt/desktop-api-key` 原子迁移完成，所有正常运行路径的明文文件读写被删除。

采用方案 A：

- Windows Credential Manager-only；
- Python child stdout HMAC readiness proof；
- endpoint 和 generation 管理状态仅由 Electron Main 持有；Bearer 由 Main生成并通过专用child env交给当前 child，但绝不进入preload/Renderer；
- Renderer 使用无凭据、无 endpoint 控制权的唯一 IPC transport。

方案 B（Credential Manager + DPAPI fallback）和方案 C（DPAPI-only）不纳入本轮。

## 2. 威胁模型与非承诺

### 2.1 必须防御

- Renderer 代码或依赖尝试使用 `fetch` 绕过 preload/Main。
- Renderer 传入外部域名、错误端口、不同协议、userinfo、fragment 或 `file:` URL。
- 本机其他进程预先占用 Agent Core 端口，并伪造公开 `/health`。
- 旧 generation、旧 proof 或旧端口在 Core 重启后继续被使用。
- 凭据以明文进入 workspace、设置 JSON、日志、trace、Renderer 响应或 Release Evidence。
- 明文迁移中断导致旧文件已删除但新凭据不可用。
- 迁移补偿错误删除迁移前就存在的有效 Credential Manager 凭据。
- 使用 junction、symlink、reparse point 或 TOCTOU 将 DPAPI 密文文件重定向到其他位置。

### 2.2 本轮不承诺

Credential Manager 和当前用户 DPAPI 都不能隔离已经在同一 Windows 用户会话中执行的恶意进程。同用户恶意进程可能调用 `CredReadW`、读取进程内存或注入 Bolt。Credential Manager 的目标是消除普通明文持久化和 Bolt 自行维护密文文件的攻击面，不宣称抵御同用户 malware。

## 3. Renderer 唯一 IPC Transport

### 3.1 单一数据流

```text
Renderer endpoint client
  -> AgentCoreTransport
  -> preload agentCoreRequest IPC facade
  -> Electron Main verified-generation gate
  -> Main-owned endpoint + Bearer
  -> verified Python Agent Core
```

生产 transport 的定义保持窄接口：

```ts
export type AgentCoreRequestHandle = {
  requestId: string;
  response: Promise<Response>;
  cancel: () => Promise<'cancelled' | 'already_finished'>;
};

export type AgentCoreTransport = (
  input: string,
  init?: RequestInit,
) => AgentCoreRequestHandle;
```

transport 同步返回 handle，因此调用方可在 response settle 前取得 request ID并取消。测试可注入返回相同 handle 结构的 InMemory transport。生产实现不得使用 global fetch fallback。

### 3.1.1 Bridge 返回值与真实 Electron composition

`Request`、`RequestInit`、`Headers`、`Response`、`AbortSignal` 和 `Error` 都不得作为 contextBridge/IPC wire value。wire contract 只允许可 structured-clone 的 plain DTO。Main 成功响应固定为：

```ts
type AgentCoreIpcResponse = {
  requestId: string;
  generationId: string;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: string;
};

type AgentCoreIpcError = {
  requestId: string;
  code: AgentCoreTransportErrorCode;
  message: string;
};
```

preload 只暴露同步 `agentCoreRequest(dto)` 和异步 `agentCoreCancel(requestId)`。`agentCoreRequest` 在调用 `ipcRenderer.invoke` 前生成 request ID并同步返回 `{ requestId, response, cancel }`；其中 `response` 只在 Renderer context 内由 adapter 将 `AgentCoreIpcResponse` 重建为真正的 `Response`。Main、preload 和 IPC 从不传递 `Response` 实例。非 2xx Core HTTP 响应仍重建为普通 `Response`；只有 transport/security failure 才 reject 为稳定 typed error。错误 DTO 不得包含 endpoint、port、token、credential ID、路径或内部异常。

Renderer 输入必须先收窄成自有 init DTO。若兼容 adapter 暂时接收 `RequestInit`，只能出现 `method`、`headers`、`body` 和本设计定义的 `timeoutMs`；`credentials`、`mode`、`cache`、`integrity`、`keepalive`、`redirect`、`referrer`、`referrerPolicy`、`signal` 及任何额外 own key 一律拒绝，不得静默忽略。body 只允许字符串；`Blob`、`FormData`、`URLSearchParams`、`ArrayBuffer`、typed array 和 stream 一律拒绝。

Main 使用 `ipcMain.handle` 注册 request/cancel channel，并在每次调用时独立完成运行时验证。preload 的校验不被视为安全边界。Main 必须验证 sender 是当前受信任 `BrowserWindow` 的存活 `webContents`，`senderFrame` 是精确允许 origin/file 的顶层 frame，不是 iframe、DevTools、已导航 frame或仅以前缀匹配的相似 origin。导航或销毁立即 abort 该 sender 全部请求。

删除 `window.bolt.agentCoreEndpoint`、preload fetch、preload 对 token/port/env 的读取，以及 Main 将 bearer/port/workspace 写回父 `process.env` 的行为。真实 endpoint 和 generation 只存在 Main；Bearer 只存在 Main 与本 generation child，且Main在child通过验证前不把它用于网络。bridge 不暴露原始 `ipcRenderer`。

必须新增真实 Electron integration test：启动真实 Electron 进程和受控 fake Core，完成 proof 后创建启用 `contextIsolation` 的真实 `BrowserWindow`，通过实际 preload/channel 验证 handle 同步返回、response Promise、DTO→`Response` 重建、cancel、导航销毁和 generation revoke。该测试还必须证明 Renderer/preload 拿不到 token、endpoint、Node API或原始 `ipcRenderer`。仅 Vitest 转译 preload 或 mock `contextBridge` 不满足本条。另在 unpacked artifact 上执行至少一项 preload/channel smoke test。

### 3.2 Core URL 没有网络控制权

Renderer 可能在兼容迁移期继续向旧 client 传入 URL 字符串，但该字符串不决定真实网络目标：

- host 无效；
- port 无效；
- scheme 无效；
- userinfo 无效；
- fragment 无效；
- Renderer header 中的 `Authorization`、`Host`、`Cookie`、`Proxy-Authorization` 会使整个请求被拒绝，网络调用次数为零。

Renderer adapter 只允许从输入中提取并校验相对 path、query、method 和 body。Electron Main 始终使用当前 `VERIFIED` generation 的 `127.0.0.1:<actual-port>`。

以下输入必须在 Renderer 或 Main 边界 fail closed：

- 非 HTTP(S) legacy URL；
- 非 loopback legacy URL；
- userinfo；
- fragment；
- 反斜杠；
- protocol-relative URL；
- path 不是单个 `/` 起始；
- path 规范化后改变 origin；
- Renderer 请求设置受保护 header；
- body 或响应超过限制；
- redirect。

Main 请求使用 `redirect: "error"`。任何 Renderer 提交的认证或受保护 header 都使整个请求返回 `CORE_HEADER_NOT_ALLOWED`，网络调用次数为零；只有输入完全通过校验后，Main 才添加自己的认证 header。

### 3.3 Main IPC 请求契约

preload 只允许向 Main 提交以下结构，未列出的字段和能力全部 fail closed：

```ts
type AgentCoreIpcRequest = {
  requestId: string;
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Array<[string, string]>;
  body?: string;
  timeoutMs?: number;
};
```

`requestId` 由 preload 使用 `crypto.randomUUID()` 在调用 IPC 前生成并立即返回给 transport 内部的 pending request handle；业务调用获得 `{ requestId, response, cancel() }`，其中 `response` 为 Promise。Main 不生成或替换 ID。规则：

- 必须是规范小写 UUID；
- 在同一 webContents 的 active request map 中唯一；重复 active ID 返回 `CORE_REQUEST_INVALID`；
- ID 只归属创建它的 webContents；
- request 到达终态后从 active map 删除；同一 ID 在该 webContents 生命周期内不得重用，Main 保留有界 recently-finished set 防止迟到 cancel 命中后续请求；
- `cancel()` 可在 response settle 前调用，并映射到 `agentCoreCancel(requestId)`；response settle 后 cancel 返回幂等 `already_finished`，不产生网络副作用。

请求约束：

- 允许方法仅为 `GET | POST | PUT | PATCH | DELETE`；`HEAD`、`OPTIONS`、`CONNECT`、`TRACE` 和自定义方法拒绝；
- `GET`、`DELETE` 不允许请求体；其他方法只允许 UTF-8 字符串 body；
- 请求体按 `TextEncoder` 后的字节数计算，最大 `4 MiB`；超限在 IPC 边界拒绝，不能发往 Core；
- path 加 query 编码后的 UTF-8 最大 `16 KiB`；
- 允许 Renderer 提交的 header 白名单只有 `accept`、`content-type`、`if-match`；header 名统一小写后检查；
- `content-type` 只允许 `application/json` 和带 UTF-8 charset 的等价形式；
- `accept` 只允许 `application/json`、`text/plain`；
- `x-bolt-request-id` 不允许由 Renderer 作为普通 header 提交；Main 只可从已验证的顶层 `requestId` 派生并添加该 header；
- header 数量最大 `16`，单个名称最大 `64 bytes`，单个值最大 `8 KiB`，全部 header 名值总计最大 `32 KiB`；按 UTF-8 bytes 计算；
- header 名必须为小写 ASCII token，值拒绝 CR、LF、NUL 和其他 C0 控制字符；
- `accept`、`content-type`、`if-match` 为 singleton，重复项一律 `CORE_HEADER_NOT_ALLOWED`，不进行逗号合并；
- hop-by-hop header、认证 header、Cookie、Origin、Referer、Host 和代理 header 全部拒绝；
- `timeoutMs` 缺省时固定为 `30_000 ms`；提供值时必须是 JSON number、有限整数且范围为 `1_000..120_000 ms`，字符串、`NaN`、`Infinity`、小数或越界值返回 `CORE_REQUEST_INVALID`，网络调用次数为零；
- Main 为每个请求创建 `AbortController`，超时、Renderer 销毁、Core generation 撤销或应用退出时必须 abort；
- Renderer 取消通过窄 `agentCoreCancel(requestId)` IPC 发出，只能取消同一 webContents 创建且仍在运行的请求；未知或跨 webContents request ID返回 `CORE_REQUEST_INVALID`且无网络副作用；已结束 ID按上述契约幂等返回 `already_finished`；
- Main 在收到响应头后按流读取并累计字节，普通响应体最大 `16 MiB`；超过上限立即 abort，不向 Renderer 返回截断成功结果；
- redirect 使用 `error`，认证不得随重定向转发；
- 每次发送、每个响应 chunk、响应 body/headers 完成处理后以及向 Renderer resolve 前，都必须原子确认 generation 仍为同一 `VERIFIED` ID；任何检查失败返回 `CORE_RESTARTED`，不返回旧 generation 成功结果。
- Main 对 IPC payload 做严格运行时 schema 验证：只接受 `Object.getPrototypeOf(value) === Object.prototype || null` 的 plain object，拒绝 array、accessor、symbol key和额外字段；header tuple 必须恰为两个字符串；所有长度限制在 Main 以 UTF-8 bytes重新计算。
- Main wire contract 只接受相对 path+query，不接受 absolute URL。canonicalization 必须拒绝 malformed percent escape、encoded slash/backslash、双重编码、dot segment、`//`、NUL/C0、lone surrogate和 fragment；只允许 checked-in `agentCoreRouteManifest.ts` 中的显式 method+path pattern。该 manifest 的初始内容必须逐项覆盖 `coreClient.ts`、`harnessClient.ts`、`harnessClientAutonomy.ts` 和 `workflowClient.ts` 的生产调用点；pattern 只允许固定 segment 加经过 `encodeURIComponent` 的单 segment ID，query key逐项列出。architecture gate 比较生产 client 调用点与 manifest：未知调用点或未被调用的宽泛 route 都失败；新增 Core route 不得自动成为 Renderer capability。
- 每个 webContents 同时最多 32 个请求，累计保留响应 body 最多 32 MiB；超限 fail closed。recently-finished request ID set 最多 4096 项、TTL 5分钟，并在 webContents 销毁时清空。
- Main 只接受响应 `content-type` 为 `application/json`、`text/plain` 或带显式 UTF-8 charset 的等价形式；body 使用 fatal UTF-8 decoder，拒绝 BOM、invalid UTF-8、声明非 UTF-8 charset及解码替换，返回 `CORE_RESPONSE_INVALID`；空 body允许。

响应契约：

```ts
type AgentCoreIpcResponse = {
  requestId: string;
  generationId: string;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: string;
};
```

只返回响应 header 白名单：`content-type`、`content-length`、`etag`、`retry-after`、`x-bolt-error-code`。不得向 Renderer 返回 `set-cookie`、认证 header、server 实现信息或未知 header。

本轮流式策略固定为不实现：

- 不注册 `agentCoreStreamOpen/Chunk/Close/Cancel` IPC；
- Renderer 请求的 `accept` 不允许 `text/event-stream`；
- 普通请求收到 `content-type: text/event-stream` 时，Main 在读取 body 前立即 abort并返回 `CORE_STREAMING_UNSUPPORTED`；
- 任何流式响应请求都不得退回 buffer-all、浏览器 fetch 或无限读取；
- 将来实现 streaming 必须另立设计，明确 stream ID 所有权、method/path allowlist、事件序号、背压、chunk/累计上限、空闲/总超时、取消和最终 generation 检查。

稳定 transport 错误至少包括：

```text
CORE_NOT_VERIFIED
CORE_RESTARTED
CORE_REQUEST_INVALID
CORE_METHOD_NOT_ALLOWED
CORE_HEADER_NOT_ALLOWED
CORE_REQUEST_TOO_LARGE
CORE_RESPONSE_TOO_LARGE
CORE_TIMEOUT
CORE_CANCELLED
CORE_STREAMING_UNSUPPORTED
```

### 3.4 生产代码门禁

`apps/desktop/src` 中禁止：

- `fetch(...)`；
- `window.fetch`；
- `globalThis.fetch`；
- `fetcher = fetch`；
- `transport = fetch`；
- `transport ?? fetch`；
- 可选的 Agent Core transport；
- Panel 直接导入底层 `harnessClient*` 网络函数。

`coreClient.ts`、`harnessClient.ts`、`harnessClientAutonomy.ts` 的 transport 参数必须显式提供。`createPanelsApi()` 捕获唯一 transport，并向 Panel 暴露已绑定的业务方法。

### 3.5 玩家发布前的 UI 要求

本 P0 实现阶段不修改 UI、CSS 或 Figma。可编辑 Core URL 的移除属于独立玩家发布 UI 门禁，不属于本地安全纵向切片的完成条件；它未完成时，即使本切片通过，项目仍禁止玩家内测和公开发布。玩家发布前必须移除当前可编辑 Core URL，或将其改为不可编辑状态：

```text
本地 Agent Core · 由 Bolt 自动管理
```

验收规则：不能保留一个看似可配置、实际不决定网络目标的地址输入框。该 UI 发布门禁必须列入 Release Evidence；在完成前不得允许玩家内测。

## 4. Agent Core 启动身份

### 4.1 `/health` 只表示 liveness

公开 `/health` 固定返回：

```json
{"status":"ok","service":"bolt-agent-core"}
```

它不返回 proof、PID、startup ID、Token、workspace、provider、路径或内部异常。它不证明服务身份，也不能使 Electron 采用一个已经占用端口的服务。

### 4.2 每个 generation 的秘密

Electron Main 为每次启动生成：

- `startupId`：随机 generation 标识；
- `bootstrapKey`：只用于 readiness HMAC；
- `bearerToken`：只用于 proof 验证后的 API 请求。

要求：

- 使用 32-byte CSPRNG；
- 不继承生产环境中的固定 Token；
- 不进入 argv、日志、错误、Renderer、preload 或 proof；
- 只通过 child 专用环境传递；
- `bootstrapKey` 在 proof 成功或失败后清除；
- `bearerToken` 在 generation 被撤销时清除。
- Core middleware 只把 `/health` 作为公开路径；`/docs`、`/redoc`、`/openapi.json` 在 desktop production composition 中禁用或同样要求认证，`OPTIONS` 不绕过认证。其余全部 route 要求唯一 `Authorization: Bearer <current-generation-token>`，header 缺失、重复、scheme大小写/空白不精确、错误/旧 token 均返回相同的 HTTP 401 + 固定无 secret JSON；使用 `secrets.compare_digest`，不记录提交值。generation child 只接受 spawn 注入的当前 bearer，撤销后进程终止，旧 bearer 在新 child 中永远无效。

### 4.2.1 Child 环境变量白名单

Python child 的环境从空对象按平台白名单重建，禁止 `{ ...process.env }`、`Object.assign({}, process.env)` 或继承后删除。Windows 只允许复制 `SystemRoot`、`WINDIR`、`ComSpec`、`TEMP`、`TMP`、`PATHEXT`、`PROCESSOR_ARCHITECTURE`、`NUMBER_OF_PROCESSORS`、`USERPROFILE`、`APPDATA`、`LOCALAPPDATA` 和由 Main 从可信安装位置重建的最小 `PATH`；开发模式可额外注入由仓库根确定的 `PYTHONPATH`，但绝不拼接父 `PYTHONPATH`。其他平台测试白名单只包含启动受信任 Python 所必需且在代码中逐项列出的变量。

父环境中所有 `BOLT_*` 先被视为不可信并全部丢弃，尤其包括 `BOLT_AGENT_CORE_TOKEN`、`BOLT_AGENT_CORE_PORT`、`BOLT_CORE_BOOTSTRAP_KEY`、`BOLT_CORE_BEARER`、旧 startup/proof 值、`BOLT_WORKSPACE`、`BOLT_EXECUTION_AUDIT_PATH`、root/src/python override及任何历史安全值。provider API key、代理 credential、`PYTHONHOME`、`PYTHONSTARTUP`、`PYTHONWARNINGS` 和攻击者 `PYTHONPATH` 不得继承。

随后只注入当前 generation 新生成的 `BOLT_CORE_STARTUP_ID`、`BOLT_CORE_BOOTSTRAP_KEY`、`BOLT_CORE_BEARER`、经锁定的 `BOLT_WORKSPACE`、runner 协议版本和必要受信任运行时路径。Python runner 读取 startup/bootstrap/bearer 后立即从 `os.environ` 移除；Agent Core 后续启动任何 tool/shell subprocess 时必须使用另一份最小环境，且不得包含 bootstrap、bearer或 provider secret。

测试必须在父进程预置恶意旧 token、旧端口、旧 bootstrap、旧 bearer、旧 workspace、provider key和攻击者 `PYTHONPATH`，断言 spawn 收到的 child env 不含任何旧值，只包含当前 generation 值；child readiness 和 HTTP auth 还必须证明未使用旧值。

### 4.3 Python desktop runner

Python child 必须自行绑定 socket：

1. host 固定为 `127.0.0.1`；
2. 默认 port 为 `0`，由 OS 分配；
3. Windows 设置 `SO_EXCLUSIVEADDRUSE`；
4. 显式端口被占时退出，不探测或采用占用者；
5. 已绑定 socket交给 Uvicorn；
6. 只有 Uvicorn 已开始监听后才生成 proof；
7. stdout 只承载 readiness 协议，普通日志全部写 stderr。

### 4.4 Readiness proof

stdout 只允许一行严格 UTF-8 JSON：

```json
{
  "type": "bolt.core.ready",
  "version": 1,
  "startup_id": "<base64url>",
  "pid": 1234,
  "host": "127.0.0.1",
  "port": 43123,
  "proof": "<base64url-hmac-sha256>"
}
```

Canonical transcript：

```text
bolt-core-ready-v1\n
<startup_id>\n
<child.pid>\n
127.0.0.1\n
<port>\n
```

硬性验证：

- 只允许一行，并以 `\n` 结束；proof 总超时固定5秒；
- stderr 单行最大16 KiB，Main 未处理累计缓存最大1 MiB，超限视为启动/运行协议失败；
- 最大 768 bytes；
- 严格 UTF-8，拒绝 BOM、NUL 和替换字符；
- JSON 拒绝重复 key；
- 字段集合必须精确匹配，不允许额外或缺失字段；
- `type` 精确匹配；
- `version === 1`；
- `startup_id` 与当前 generation 精确匹配；
- `pid === child.pid`；
- `host === "127.0.0.1"`；
- `port` 为 OS 返回的实际绑定端口；显式端口模式还必须等于配置端口；
- proof 为规范 base64url，解码后恰好 32 bytes；
- HMAC-SHA256 使用常量时间比较；
- proof 只能消费一次；旧 generation proof 和重放必须拒绝；
- proof 后出现第二行或额外 stdout 数据视为协议失败。Main 在 child 全生命周期持续监控 stdout，proof 后任何额外 byte 立即撤销 generation、abort 请求并终止 child；stderr 采用有界逐行转发，单行和累计缓存均有限制，避免内存耗尽。
- `startupId` 为32随机 bytes的无 padding规范 base64url；解码长度必须恰为32，拒绝任何等价但非规范编码。

### 4.5 失败清理是原子安全动作

任何 proof 失败、端口占用、child 提前退出、超时或 strict health 失败，必须立即执行：

1. 将 generation 状态转为 `FAILED/REVOKED`，阻止新请求；
2. 注销任何捕获 generation 能力的 handler；生产 composition 保留一个永久、无 endpoint/token 的 gated request/cancel handler，使运行期窗口稳定返回 `CORE_NOT_VERIFIED`，初次启动验证前不创建窗口因此不存在 Renderer 可调用能力；
3. abort 所有尚未发出的 Main 请求；
4. kill child，并等待退出或执行有界强制终止；
5. 清空 endpoint、bootstrap key、Bearer 和 generation 引用；
6. 初次启动时不创建 `BrowserWindow`；
7. 运行期失败时保留窗口，但 IPC 返回 `CORE_NOT_VERIFIED`，网络调用次数必须为零。

清理动作必须是幂等的，child `exit`、timeout 和 malformed proof 并发到达时只能有一个终态。

### 4.6 严格启动顺序

```text
spawn
-> bind/listen
-> stdout proof
-> proof verification
-> strict /health liveness：只请求 proof 的精确 endpoint；HTTP 200；redirect error；总超时5秒；body 最大4 KiB；严格 UTF-8与拒绝重复 key的 JSON；字段集合精确为 `status`,`service` 且值为 `ok`,`bolt-agent-core`。该请求不携带 Bearer
-> VERIFIED generation
-> register IPC
-> create BrowserWindow
```

禁止在 proof 验证前：

- 创建 Renderer bridge capability；
- 注册可发送 Core 请求的 IPC；
- 发送 Bearer；
- 接受已存在的 `/health` 服务。

### 4.7 Core 重启

Core 退出后立即撤销旧 generation。新 generation 使用新的 startup ID、bootstrap key、Bearer 和 OS 分配端口。Renderer bridge 不缓存 endpoint。任何 in-flight 请求在 generation 改变时返回 `CORE_RESTARTED`，不自动重放 POST、PUT、PATCH 或 DELETE。

## 5. Windows Credential Manager-only

### 5.1 选择理由

本轮优先 Windows Credential Manager，而不使用 DPAPI 文件：

- 不需要 Bolt 自行管理密文文件、ACL、原子 rename、junction、symlink 和 reparse point；
- 不存在 `Path/lstat` 检查后再用普通路径 I/O 的 TOCTOU；
- `Advapi32` 为 Windows 系统组件，不增加第三方依赖；
- provider API Key 预期小于 Credential Manager 的 2560-byte blob 限制。

### 5.2 Adapter

生产 adapter：

- `CredWriteW`；
- `CredReadW`；
- `CredDeleteW`；
- `CredFree`；
- `CRED_TYPE_GENERIC`；
- `CRED_PERSIST_LOCAL_MACHINE`。

`LOCAL_MACHINE` 在这里表示当前 Windows 用户的本机持久化，不表示所有用户共享。

Native API 必须注入到 store，普通单元测试使用 fake API；Windows-only 集成测试使用随机测试 target，并在 `finally` 删除。

### 5.3 Credential identity

每个 provider 使用 provider-independent、随机、版本化 ID：

```text
wincred.v1.<uuid>
```

Credential Manager target：

```text
dev.bolt.desktop/model/v1/<credential-id>
```

ID 和 target 不包含 provider 名称、endpoint、用户名、邮箱、模型 ID、Key 前缀、Key 长度或 workspace。

### 5.4 大小与错误行为

- secret 按 UTF-8 byte length 计算；
- 1–2560 bytes 接受；
- 0 bytes 返回 `credential_secret_empty`；
- 2561 bytes及以上返回 `credential_secret_too_large`；
- access denied、store unavailable、corrupt、not found 或临时错误均不触发 DPAPI fallback；
- `CredDeleteW` 的 not found 映射为幂等成功；
- 所有 `CredReadW` 成功返回的 native 内存，无论解码成功或失败，都必须 `CredFree`。

稳定错误码：

```text
credential_invalid_id
credential_secret_empty
credential_secret_too_large
credential_not_found
credential_store_unavailable
credential_access_denied
credential_write_failed
credential_read_failed
credential_delete_failed
credential_corrupt
credential_encoding_invalid
credential_revision_changed
credential_migration_additional_legacy_key
credential_migration_conflict
credential_migration_failed
```

### 5.5 正常 API Key 生命周期

正常生命周期使用以下持久化状态；所有状态都属于 provider 非敏感配置并与 revision 一起原子写入：

```text
absent
credential_write_pending
active
credential_switch_pending
credential_cleanup_required
credential_deleting
credential_recovery_required
```

操作开始时的 gate 不是仅存在于进程内：

- 新增在生成 ID后、调用 `CredWriteW` 前持久化 `credential_write_pending`、attempt ID和目标 ID；
- 替换在写新凭据前持久化 `credential_switch_pending`、attempt ID、旧 ID和新 ID；旧 ID仍记录但 Gateway 在 pending 状态拒绝调用；
- 删除在 native delete 前持久化 `credential_deleting`、attempt ID和待删除 ID，并清空 active ID；
- 每个 commit、rollback 或 recovery transition 都增加 revision并重新加载验证；
- 进程崩溃后按持久化 attempt ownership恢复，不能仅依赖内存锁。

- `credential_write_pending`：若尚无 native write attempt evidence，回到 `absent`；若 write 已返回但 ownership marker 未持久化，转 `credential_recovery_required` 且绝不自动删除；若 marker=true，则读回，匹配后继续 config switch，不匹配/不可读则仅删除 attempt-owned target，删除无法确认时转 recovery。
- `credential_switch_pending`：新 target marker=false按上述未知归属恢复；marker=true且 config仍指旧 ID时验证旧凭据并删除新 target后回到 `active`；config已指新 ID时完成 reload+二次读回，成功后清理旧 ID，否则尝试恢复旧 config，任一步无法确定转 recovery。
- `credential_cleanup_required`：验证 config仍指新 active ID且新凭据可读后，只重试删除记录的旧 attempt-owned ID；不得重写或切换 credential。
- `credential_deleting`：config active必须为空；只重试删除待删除 ID，not found视成功，然后提交 `absent`。若 config仍 active或 revision不符，转 recovery，不重新启用旧 ID。
- `credential_recovery_required`：自动流程只做只读诊断和确定性、ownership有证据的补偿；任何归属或 revision不确定保持阻断，禁止猜测删除。

正常生命周期 crash checkpoints 固定为：pending journal commit前/后、native write调用前/返回后、ownership marker前/后、首次 readback前/后、config switch前/后、reload前/后、二次 readback前/后、旧 credential delete前/后、最终 state commit前/后；删除流程另覆盖disable commit前/后、native delete前/后和absent commit前/后。每一点重启测试必须断言上述确定状态、active引用存在性、凭据保留/删除集合和Gateway零网络调用。

所有新增、替换和删除操作按 provider 串行，并使用非敏感配置 revision 防止旧请求覆盖新状态。Gateway 只允许 `credential_state=active` 且配置中存在当前 `active_credential_id` 时调用；每次模型调用前重新从 Credential Manager 加载，不缓存长期明文。

#### 新增 API Key

1. 校验 provider revision、secret 非空且 UTF-8 不超过 2560 bytes。
2. 生成新的 provider-independent `credential_id`；不得覆盖未知已有 target。
3. `CredWriteW` 写入新凭据。
4. `CredReadW` 读回并在内存中精确比较。
5. 原子写入非敏感配置，将 `active_credential_id` 从 `null` 切换为新 ID并增加 revision。
6. 重新加载配置，确认 revision 和 ID。
7. 再次读取凭据确认可用。
8. 原子把 `credential_write_pending` 提交为 `active`、保留新 `active_credential_id`并增加 revision；重载确认 active/revision后才暴露 `has_api_key=true`。
9. 只有第 3–8 步全部成功后，独立 provider verification state 才进入 `unverified`，允许后续显式模型验证；`unverified` 不改变 credential state=active，是否允许真实调用由明确验证入口决定，本轮默认仅验证调用可用，普通模型调用在 provider verified 前阻止。凭据写入成功不等于模型 verified。

失败回滚：

- 第 3 步调用成功后，无论后续读回能否确认，都必须把该 target 视为本操作拥有并尝试幂等删除；
- 第 3 或 4 步失败且补偿删除确认成功：配置恢复为原状态；
- 写可能已成功但补偿删除失败或无法确认：保留持久化 attempt ID/目标 ID，进入 `credential_recovery_required`，配置不得 active，模型调用被阻止；
- 第 5–7 步失败：先恢复并重新加载原配置，再删除本次新建凭据；
- 恢复配置或补偿删除失败：provider 进入 `credential_recovery_required`，阻止模型调用；
- 任一失败不得留下配置指向不存在凭据。

#### 替换 API Key

替换不得原地覆盖当前活动 target，因为配置失败后无法恢复旧 secret。使用 copy-switch-cleanup：

1. 读取并锁定原 `active_credential_id` 和 provider revision。
2. 新建不同 `credential_id`，写入新 secret并读回验证。
3. 原子切换配置到新 ID并增加 revision。
4. 重新加载配置并从新 ID读回验证。
5. 原子把 `credential_switch_pending` 提交为 `active`、保留新 ID并增加 revision；重载确认后才允许进入旧凭据清理。
6. 切换成功后才删除旧 ID。
7. 旧 ID删除失败时，新配置保持有效，但 provider 进入 `credential_cleanup_required`；记录不含 target/secret 的待清理引用并禁止再次替换或删除，直到清理完成。模型调用可否继续必须由状态明确决定：本轮固定为阻止真实模型调用，避免长期双凭据状态。

失败回滚：

- 配置切换前失败：删除本次新建凭据，保留旧配置和旧凭据；
- 配置切换后验证失败：尝试恢复旧配置并重新加载；只有旧配置和旧凭据都验证可用后，才删除新凭据并完成回滚；
- 旧配置恢复成功但旧凭据不可读、损坏或无法验证：进入 `credential_recovery_required`，保留新凭据和旧凭据作为恢复材料，active ID保持空，阻止模型调用，不宣称回滚成功；
- 旧配置恢复失败或新凭据补偿删除失败：进入 `credential_recovery_required` 并阻止模型调用；
- 旧凭据不得在配置切换、重新加载和新凭据读回验证完成前删除。

#### 删除 API Key

删除使用 disable-delete-commit，避免配置继续引用已删除凭据：

1. 锁定 provider revision 和当前 ID。
2. 原子将配置切换为 `credential_state=credential_deleting`，保留待删除 ID，但 `active_credential_id=null`；此状态立即阻止新模型调用。
3. 重新加载配置，确认没有活动 ID。
4. `CredDeleteW` 删除待删除凭据；not found 视为幂等成功。
5. 原子清除待删除 ID，设置 `credential_state=absent` 并增加 revision。
6. 重新加载确认没有活动或待删除凭据。

失败恢复：

- 第 2 或 3 步失败：凭据保留，尝试恢复原配置并重新加载验证；
- 原配置恢复写入或 reload 验证失败：进入 `credential_recovery_required`，保留待删除 ID，active ID为空，阻止模型调用；
- 第 4 步失败：保持 `credential_deleting` 和待删除 ID，阻止模型调用，允许重试删除；不得把旧凭据重新设为 active；
- 第 5 或 6 步失败：凭据已不存在，配置保持非 active 的 recovery 状态，启动恢复负责完成清理；
- 删除操作不得先删 Credential Manager 凭据再清空 active 配置。

#### 并发与模型调用阻断

以下状态一律禁止真实模型调用：

```text
credential_write_pending
credential_switch_pending
credential_cleanup_required
credential_deleting
credential_recovery_required
credential_migration_failed
credential_migration_conflict
```

模型调用在读取配置 revision 后、加载凭据前再次确认 revision；创建 provider client 前再确认一次。若期间发生替换或删除，返回 `credential_revision_changed`，不得使用已经加载的旧 secret。删除和替换开始后，排队但尚未发出的调用必须失败；已经发送到第三方的请求无法撤回，但不得自动重试。

#### 正常生命周期 TDD 验收

必须先观察以下测试失败：

- 新增：写入、读回、配置切换和二次读回全部成功后才暴露 `has_api_key=true`；
- 新增：配置写入失败时删除本次新凭据，配置仍为空；
- 新增：`CredWriteW` 成功但首次读回失败时仍尝试删除本次 target；删除成功恢复原状态，删除失败进入 recovery；
- 新增：补偿删除或配置恢复失败进入 recovery，模型调用被阻止；
- 替换：新 ID与旧 ID不同，切换验证前旧凭据保持存在；
- 替换：新凭据写入/读回失败时旧配置和旧凭据不变；
- 替换：切换后验证失败时，只有旧配置和旧凭据都验证通过才删除新凭据并完成回滚；旧凭据验证失败则保留双方并进入 recovery；
- 替换：旧凭据清理失败进入 cleanup-required，不静默成功，模型调用被阻止；
- 删除：先将 active ID清空并验证，再调用 `CredDeleteW`；
- 删除：native delete 失败时保持 deleting 状态和待删除 ID，模型调用被阻止；
- 删除：进入 deleting 后恢复原配置写入或 reload 失败时进入 recovery，active ID保持空；
- 删除：not found 幂等完成；
- 并发替换/删除按 provider 串行，过期 revision 不能覆盖新配置；
- 调用期间 revision 改变返回 `credential_revision_changed`，不构造 provider client；
- API、日志、trace 和状态响应只暴露状态与稳定错误码，不含 secret、target 或旧/new credential ID。

### 5.6 DPAPI 文件禁令

DPAPI 文件存储不得接入生产 composition。生产凭据代码禁止使用以下方式存储 secret：

- `Path.read_bytes/write_bytes/read_text/write_text/unlink`；
- `Path.exists/lstat/resolve` 作为安全边界；
- 普通完整路径上的 `os.open/os.replace`；
- workspace 或 user-data 下的自管 `.bin` 密文文件。

如果未来选择 DPAPI 文件，必须另立 ADR，采用从磁盘根逐组件、不跟随 reparse point、持有目录和文件句柄的 Windows-only adapter。该未来方案至少需要 `CreateFileW`、`FILE_FLAG_OPEN_REPARSE_POINT`、`GetFileInformationByHandleEx`、`GetFinalPathNameByHandleW` 和 handle-based read/write/rename/delete。本轮不实现，也不得作为运行时 fallback。

## 6. 旧明文 Key 原子迁移

### 6.1 迁移范围与旧路径

每次迁移只处理用户当前明确选中并已锁定的一个工作区：

```text
<selected-workspace>/.bolt/desktop-api-key
```

迁移入口必须收到经过现有 workspace/path guard 验证的 `selected_workspace`，并在操作期间绑定其 workspace identity/revision。禁止：

- 扫描最近工作区、workspace history、磁盘目录或父目录；
- 使用 glob、递归搜索或索引寻找其他 `.bolt/desktop-api-key`；
- 启动时批量迁移所有已知工作区；
- 在当前选中工作区之外读取、比较、删除或报告旧 Key；
- 将一个工作区的旧 Key自动应用到另一个工作区/provider。

如果用户切换工作区，当前迁移必须在任何 secret 读取前 abort；若已进入 Credential Manager/config 操作，则按本节回滚规则完成或恢复后再允许切换。

“发现第二份旧 Key”的稳定行为定义为：

1. Bolt 不主动发现第二份，因为禁止扫描；
2. 当用户以后明确选择另一个工作区，且该工作区也存在旧文件时，将其视为独立 migration candidate；
3. 如果当前 provider 已有 active credential，不自动覆盖、不比较两个工作区的 secret，也不读取第二份内容用于冲突判断；
4. 返回 `credential_migration_additional_legacy_key`，保留第二份旧文件和现有凭据/配置，阻止该工作区的真实模型调用；
5. UI 后续必须让用户明确选择“保留现有凭据并删除/忽略该工作区旧 Key”或“为该工作区创建独立 provider credential”；本 P0 不自动执行该决策；
6. 状态和审计只记录匿名 workspace ID、候选存在和稳定错误码，不记录路径、secret、长度、前缀或 hash。

若同一工作区重复进入迁移，则使用 journal 幂等恢复，不算第二份旧 Key。

该文件只可由 migration 模块在当前选中工作区读取；正常设置、模型调用和 provider 运行时不得读取或写入它。

### 6.2 Migration journal

非敏感配置必须记录：

- migration schema version；
- 目标 `credential_id`；
- provider/config revision；
- 状态：`pending | committed | committed_cleanup_required | failed | conflict | additional_legacy_key | recovery_required`；
- 当前选中 workspace 的匿名稳定 ID与 workspace revision；
- attempt ID及目标 `credential_id`；
- 本次迁移是否创建了新凭据 `created_by_attempt`。

在调用 `CredWriteW` 前，必须先原子持久化 `pending`、attempt ID、目标 ID、workspace ID/revision 和 `created_by_attempt=false`。`CredWriteW` 成功返回后立即将同一 attempt 更新为 `created_by_attempt=true`，再进行读回。若进程在 write 返回与 marker 更新之间崩溃，恢复流程将该目标视为“归属不确定”：不得当作预先存在凭据，也不得自动删除；原子转为 `recovery_required`，阻止模型调用，直到通过 attempt/config 证据人工或确定性恢复。

journal 不记录 secret、长度、前缀、hash、target 或完整 workspace 路径。

### 6.3 成功顺序

1. 加载当前选中 workspace 的 identity/revision、workspace-scoped migration journal 和 provider 非敏感配置；先解释持久化 journal，`failed | conflict | additional_legacy_key | recovery_required | committed_cleanup_required` 不得因 legacy 文件当前不存在而被绕过。
2. 只有 journal 允许开始新 attempt 时才检查旧文件；如果不存在，返回 `absent`。
3. 如果 provider 已有 `credential_state=active` 和 `active_credential_id`：只确认 legacy candidate 文件存在，不打开或读取内容；原子持久化该 workspace 的 journal `status=additional_legacy_key`，返回 `credential_migration_additional_legacy_key` 并阻止该 workspace 模型调用。
4. 如果 journal 已为 `additional_legacy_key`，持续阻止该 workspace 模型调用；不打开或读取 legacy 文件。
5. 仅在没有 active credential 且不是 additional-legacy 状态时，使用二进制 bounded read，最多尝试读取 `2561 bytes`：读取到第 `2561` byte 即返回 `credential_secret_too_large`，不得继续或先无上限载入。严格 UTF-8 解码前 1–2560 bytes，拒绝 BOM、NUL 和解码替换；不自动 trim空格或换行，文件 bytes即 secret bytes；空内容拒绝。
6. 读取或建立非敏感 migration attempt、目标 `credential_id` 和 ownership 状态。
7. 如果目标凭据不存在，本次创建它，并记住 `created_by_attempt=true`。
8. 如果目标凭据已存在，读回比较：
   - 内容一致：复用，`created_by_attempt=false`；
   - 内容不同：返回 `credential_migration_conflict`，保留旧文件和原凭据。
9. 从 Credential Manager 读回目标凭据并在内存中精确比较。
10. 原子提交非敏感的待验证状态，同时写入：
    - `pending_active_credential_id=<目标 ID>`，`active_credential_id=null`；
    - `credential_state=credential_switch_pending`；
    - migration journal `status=pending`及阶段 `config_switched`；
    - 新 provider/config revision。
11. 重新从持久化配置加载，并确认 pending ID、credential state、journal阶段和 revision 全部匹配。
12. 再次从 Credential Manager 读取并验证凭据可用。
13. 原子提交最终状态：`active_credential_id=<目标 ID>`、清空pending ID、`credential_state=active`、journal `status=committed_cleanup_required`，增加revision并重载验证。Gateway在此状态仍阻止调用。
14. 在同一 workspace lock 下，以 Windows handle-based no-follow 操作重新验证 legacy 文件 identity 后删除旧明文文件；逐组件拒绝 reparse point，读取和删除前验证 regular file、identity和大小，不能仅靠 path/lstat/resolve。
15. 确认同一 file identity 已不存在；删除或确认失败时保持 `committed_cleanup_required`，保留有效新凭据和配置但阻止该 workspace 真实模型调用，后续只能在再次验证相同 config/credential/file identity 后重试清理，不得重写凭据。
16. 原子将 journal 从 `committed_cleanup_required` 收敛为 `committed`并重载验证，返回 `migrated`。

只有第 10–13 步全部确认后，才允许删除旧文件。

### 6.4 回滚规则

如果本次迁移新建了 Credential Manager 凭据，但后续非敏感配置写入或验证失败：

1. 保留旧明文文件；
2. 只有 `created_by_attempt=true` 时才删除本次新建凭据；
3. 删除补偿失败时返回稳定失败并阻止模型调用；
4. 不得把配置写成指向已删除的 credential；
5. 如果配置曾写入，必须先恢复原非敏感配置并验证，再删除新凭据。

如果目标凭据在迁移前已存在且内容一致：

- 任何失败都不得删除它；
- 保留旧明文文件；
- 保留迁移前配置；
- 下一次启动可重试。

如果目标凭据已存在但内容不同：

- 返回 conflict；
- 不修改配置；
- 不删除旧文件；
- 不覆盖或删除已有凭据。

任何失败都不得留下：

- 配置指向不存在凭据；
- 旧文件已删除但新凭据不可用；
- 因补偿错误删除预先存在的凭据；
- 正常模型调用继续读取旧明文文件。

### 6.4.1 Workspace-scoped Gateway gate

每次真实模型调用必须先绑定服务端已锁定的 workspace identity/revision，禁止使用 UI 当前选择、默认 workspace、启动缓存或请求 body 中未经验证的路径。Gateway 只能通过单一 credential resolver 获取短生命周期 secret lease：

```py
resolve_model_credential(
    locked_workspace_identity,
    locked_workspace_revision,
    provider_id,
) -> CredentialLease
```

resolver 在任何 `CredReadW`、provider client 构造和外部网络前，基于当前锁定 workspace 从持久化存储重新读取 migration journal及其 revision。`pending | failed | conflict | additional_legacy_key | recovery_required | committed_cleanup_required` 全部阻止该 workspace 的真实模型调用；provider credential state 非 `active` 也阻止。journal read error、未知 schema、identity/revision mismatch 一律 fail closed。

读取 provider config revision和 active credential 后，resolver 在 `CredReadW` 前、读回后及 provider client 构造前再次比较 workspace revision、migration revision和provider config revision；任一改变即清除短生命周期 secret并返回 `credential_revision_changed`，网络调用为零。secret 不进入 `ModelConfig`，不跨调用缓存。

迁移状态是 workspace-scoped，credential state 是 provider-scoped，两套状态正交。A workspace 为 committed/active 时可调用；B workspace 的 `additional_legacy_key`、pending、failed、conflict、recovery或cleanup状态只阻止 B，即使 A/B 使用同一 provider或active credential也不互相放行/阻断。重启后必须重新从持久化 journal得到同样结果。生产 fake provider也不得绕过 gate；只有显式测试 composition可注入无网络 resolver。

稳定错误 `credential_migration_additional_legacy_key` 不得降级为 credential_not_found或普通 provider failure。

### 6.5 正常运行时改造

迁移切换后：

- `DesktopSettingsService` 不再保存、加载或删除明文 API Key 文件；
- `ModelConfig` 不持有长期 `api_key`；
- 非敏感配置只持有 `credential_id`；
- Gateway 在每次调用前加载凭据；
- 删除凭据后，新调用立即返回 `credential_not_found`；
- 不缓存旧 key；
- migration 为 `failed | conflict | additional_legacy_key` 时阻止对应 workspace 的真实模型调用。

## 7. TDD 验收矩阵

### 7.1 Renderer transport

必须先观察以下测试失败：

- `agentCoreRouteManifest.ts` 与所有生产client调用点精确双向匹配，未知route、宽泛pattern和未清单query key使gate失败；
- gate 遇到 `fetcher = fetch`、可选 transport 或 Panel 直引 client 时失败；
- 挂载全部 Panels，global fetch 被设为“调用即失败”，当前代码触发红灯；
- 所有 endpoint clients 缺少 transport 时 TypeScript/build 失败；
- Renderer 传入外部 host、错误 port、scheme、userinfo、fragment或任一非法 canonicalization 输入时明确拒绝，网络调用次数为零；合法输入的真实目标始终是 verified endpoint；
- Renderer 传入受保护 header 时，Main 返回 `CORE_HEADER_NOT_ALLOWED`，网络调用次数为零；通过校验后才添加 Main 自有认证；
- redirect 被拒绝；
- generation 未验证时请求返回 `CORE_NOT_VERIFIED`，网络调用为零；
- 未允许的方法、header、content type 或额外 IPC 字段 fail closed；
- Renderer sender trust matrix：development只接受Main启动时记录的dev server精确origin且顶层frame URL pathname在应用入口allowlist；packaged只接受当前asar/unpacked应用根下规范化后的精确`file:`入口，拒绝相似前缀、iframe、DevTools、导航后旧frame；
- header 数量、单项/总 bytes、控制字符、大小写、singleton重复和受保护 header边界全部受测；
- timeout 缺省为30秒，非有限数、非整数、字符串和越界值返回 `CORE_REQUEST_INVALID`且网络调用为零；
- GET/DELETE body 被拒绝，4 MiB请求体边界和16 MiB响应体边界按 UTF-8/实际 bytes执行；
- 默认、最小和最大 timeout 生效，超时会 abort底层请求；
- Renderer cancel、webContents销毁和 generation撤销均取消请求，跨 webContents取消被拒绝；
- 未实现 stream IPC前，SSE Accept 被拒绝；意外 SSE响应在读取 body前 abort并返回 `CORE_STREAMING_UNSUPPORTED`，不得 buffer-all或调用 global fetch；
- 空响应、最后 chunk后撤销 generation以及 resolve前撤销都返回 `CORE_RESTARTED`；
- response invalid UTF-8、BOM、非 UTF-8 charset或不允许 content-type 返回 `CORE_RESPONSE_INVALID`，不向Renderer返回替换字符串；

### 7.2 Core 身份与端口抢占

必须先观察以下测试失败：

- 假 localhost `/health` 返回 `status=ok`，Supervisor 不得采用；
- HTTP 500 但 body 为 ok，不得采用；
- 显式端口被占，child 返回 `PORT_IN_USE`；
- 假服务从未收到 Bearer；
- proof 总超时5秒的边界、stderr 16 KiB单行/1 MiB累计边界受测；
- startup ID、PID、host、OS 实际端口、版本或 HMAC 任一不匹配均失败；
- `/health` 以外 route 对缺失、重复、畸形、错误和旧 Bearer统一401且无secret；docs/openapi和OPTIONS在production不能绕过认证；
- proof 重放或第二行 stdout 失败；
- proof 后 strict health 失败时 kill child；
- 每个失败路径都关闭 IPC、清空 generation、endpoint、bootstrap key 和 Bearer；
- 初次启动失败时 `BrowserWindow` 构造次数为零；
- Core exit 后旧 generation 请求不发网络；
- 重启后旧 proof、旧 endpoint 和旧 Bearer 无效。

### 7.3 Credential Manager

必须先观察以下测试失败：

- 2560 UTF-8 bytes 成功，2561 bytes稳定拒绝；
- Unicode 按 UTF-8 bytes 计数；
- target 不泄露 provider metadata；
- overwrite 同一 ID；
- delete not found 幂等；
- access denied 不 fallback；
- 非 UTF-8 blob 返回 `credential_encoding_invalid`；
- `CredFree` 在成功、decode 失败和异常路径都调用；
- Windows synthetic round-trip 成功且清理测试 target；
- static gate 确认生产不引用 DPAPI file store 或普通 secret 文件 I/O；
- 运行后磁盘上不存在由生产 store 创建的 credential `.bin` 文件。

### 7.4 迁移与回滚

必须先观察以下测试失败：

- 写入并读回 Credential Manager 成功后才删除旧文件；
- 新建凭据后配置写入失败，只删除本次新建凭据并保留旧文件；
- 预先存在且内容一致的凭据在任何失败后都保留；
- 预先存在且内容不同返回 conflict，双方都保留；
- 配置持久化成功但重新加载失败时恢复原配置，保留旧文件；
- 补偿删除失败时迁移失败并阻止模型调用；
- 删除旧文件失败时迁移失败，新凭据和有效配置保持可重试状态；
- 每个 crash checkpoint 重跑具有幂等结果；
- 不存在配置指向缺失凭据；
- API、日志、trace、快照和 Release Evidence 不含 secret；
- static gate 确认只有 migration 模块可读取旧路径，任何模块都不得写入旧路径；
- migration API 没有 workspace collection、history、glob 或 recursive scan 参数；
- bounded read 对 2560/2561/更大文件、严格 UTF-8、BOM、NUL 和结尾换行具有确定行为；
- journal 在 Credential Manager write 前持久化 attempt/target ownership，write 后 marker 更新前崩溃进入归属不确定 recovery，不误删或误认预存凭据；
- 两个工作区都存在旧文件时，选择工作区 A只访问 A；工作区 B的 fake filesystem read/delete 调用数为零；
- 后续明确选择工作区 B且已有 active credential 时，持久化 workspace-scoped `additional_legacy_key`，返回 `credential_migration_additional_legacy_key`，不读取 B 的 secret、不改变现有凭据、不删除 B 文件；
- 重启后 workspace B的 additional-legacy 状态仍使 Gateway 阻止真实模型调用，workspace A不受影响；
- migration 期间 workspace identity/revision 改变时 abort并执行安全回滚。

## 8. 执行顺序与停止条件

固定顺序：

1. Renderer 唯一 IPC transport；
2. stdout HMAC readiness proof 与 Main-owned Bearer；
3. Windows Credential Manager-only；
4. 旧明文 Key 迁移、回滚及正常运行时切换；
5. 四项联合安全回归、Desktop build 和后端 focused tests。

每个行为严格执行：

```text
RED test
-> 观察正确失败
-> 最小实现
-> focused GREEN
-> 规格审查
-> 代码质量/安全审查
-> 下一行为
```

停止条件：

- 同一问题连续三轮失败；
- 需要修改 UI、CSS、Figma 或无关功能；
- 需要清理、重置、覆盖或提交现有未提交改动；
- Credential Manager 真机环境不可用；
- proof/端口设计与 Electron/Python 实际运行时冲突；
- 发现 secret 进入日志、trace、Renderer 或 Git；
- 测试失败原因不清楚。

## 9. 完成定义

只有以下全部满足，P0 安全切片才可标记完成：

- preload 只接收/返回可复制 DTO，Renderer adapter 才创建 `Response`；真实 Electron `BrowserWindow + contextIsolation` integration test 覆盖同步 handle、Promise、cancel、导航销毁与 restart，而非仅转译 preload；
- child env 从最小白名单重建，恶意父环境旧 token/port/bootstrap/bearer/workspace/PYTHONPATH 不被继承或使用；
- A workspace 可调用、B workspace 因 `additional_legacy_key` 被阻止、重启后 B仍被阻止且 A不受影响；两者网络调用计数符合预期；
- Renderer production code 没有 Agent Core global fetch fallback；
- 所有 Panel 和 client 通过唯一 IPC transport；
- Core URL 不决定真实网络目标；
- 玩家发布 UI 的可编辑 Core 地址门禁单独记录为未完成，因本轮禁止修改UI而不阻止安全切片技术验收，但持续禁止玩家内测和公开发布；
- 假 `/health` 和端口抢占无法获得 Bearer；
- proof 所有严格校验和失败清理测试通过；
- Bearer 只在 Electron Main 和本 generation child 中存在，且Main仅在child已验证后用于HTTP；
- Windows Credential Manager 真机往返通过；
- 新增、替换、删除 API Key 的 copy-switch-cleanup、disable-delete-commit、回滚、清理和模型调用阻断测试全部通过；
- DPAPI 文件 store 未接入生产；
- 迁移成功、失败、冲突、崩溃恢复和补偿回滚测试全部通过；
- 所有旧明文正常读写路径删除；
- focused Desktop tests、backend tests、architecture gate 和 Desktop build 通过；
- 对已有整套 UI 测试失败单独如实记录，未将其冒充本轮通过；
- Release Evidence 证明上述状态且不含 secret。

四项全部通过前，项目状态必须保持：

```text
开发中
P0 安全切片未完成
禁止玩家内测
禁止公开发布
```
