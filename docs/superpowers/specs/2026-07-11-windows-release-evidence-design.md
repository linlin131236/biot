# Bolt Windows 发布证据纵向切片设计

- 日期：2026-07-11
- 状态：实施中
- 分支：`feat/safe-controlled-beta`
- 前置：
  - P0 本地安全纵向切片技术验收完成
  - 玩家发布 UI 门禁切片完成（Desktop 450 全绿，Renderer 无 Core URL 权威）
- 范围：可重复 Windows 打包、安装运行验证、签名入口、自动更新与回滚、崩溃与反馈、产物安全检查、干净环境验收、Release Evidence
- 发布状态：本切片完成后**仍不得自行对玩家分发**；只有签名、真实安装、更新回滚、崩溃脱敏、干净 Windows 与 Release Evidence 全部通过，才可建议“玩家小范围内测”，最终分发须用户明确授权
- 与旧文档关系：
  - 本设计 **supersedes** `docs/superpowers/plans/2026-07-10-release-evidence-windows.md` 中与当前代码冲突或未覆盖的部分
  - 旧计划中的 evidence schema / atomic store / Windows acceptance check IDs **仍有效**，作为 Task H 的实现基线，不重复造第二套 schema

## 1. 目标

让 Bolt 从“团队内部可验证”推进到“具备玩家小范围内测的技术条件”。

完成定义（全部为真才可建议小范围内测）：

1. 可重复生成 Windows 安装产物（dir / portable / nsis），不依赖开发服务器、不要求用户预装 Node/Python/uv。
2. 安装后 Main 能启动随包分发的 Agent Core；Renderer 仍无 endpoint/Bearer/ipcRenderer。
3. 代码签名配置安全且可验证；无合法证书时标记 `release_signing_blocked`，不伪造。
4. 自动更新信任链可本地验证（HTTPS、签名/哈希、失败回滚、任务中不强制更新）；无生产更新服务器时不得声称生产更新链完成。
5. 崩溃与反馈本地可诊断、默认不上传、脱敏可复制。
6. 产物安全扫描与 SBOM/SHA-256 完成。
7. 干净 Windows 验收通过，或诚实记录 `clean_windows_e2e_blocked` 并交付一键脚本。
8. Release Evidence 全绿且无敏感信息。

明确不做：

- 不 push、不创建公开 Release、不上传安装包到外部
- 不购买证书、不使用未知证书
- 不修改已验收 P0 安全边界与玩家 UI 门禁结论
- 不把 unsigned 说成 signed，不把开发启动说成安装版 E2E

## 2. 安装包格式

| 产物 | 用途 | 命令 |
|------|------|------|
| `win-unpacked/` | 目录布局 smoke、产物检查、本地启动 | `package:win:dir` |
| Portable `.exe` | 免安装冒烟 / 轻量分发 | `package:win:portable` |
| NSIS installer | 正式安装/卸载/升级路径 | `package:win:nsis` |

版本源：根 `package.json` 与 `apps/desktop/package.json` 的 `version` 必须一致；electron-builder 以 desktop package version 为准。CI 与本地证据写入同一 `version` + `git rev-parse HEAD`。

## 3. 打包工具与 Vite/Electron 结合

现有链路保持：

```text
pnpm --filter @bolt/desktop build
  -> vite build (Renderer dist/)
  -> tsc -p tsconfig.electron.json (dist-electron/)
pnpm package:win:*
  -> release-preflight.mjs (GitHub assets 可达性)
  -> run-electron-builder.mjs (超时/空闲保护)
  -> electron-builder --config electron-builder.json --publish never
  -> package:win:dir 额外 check-desktop-package-runtime.mjs --require-output
```

约束：

- `--publish never` 强制，禁止隐式发布
- `electronDist: node_modules/electron/dist` 复用本地 Electron，减少下载
- 构建后可调用 `scripts/create-release-evidence.mjs` 生成哈希与环境清单

## 4. Python Agent Core 随应用打包

`electron-builder.json` extraResources：

| from | to |
|------|----|
| `services/agent-core/src` | `agent-core/src` |
| `services/agent-core/pyproject.toml` | `agent-core/pyproject.toml` |
| `services/agent-core/.venv` | `agent-core/.venv` |

packaged Main 通过 `process.resourcesPath/agent-core` 解析：

- Python：`resources/agent-core/.venv/Scripts/python.exe`
- module：`python -m bolt_core.desktop_runner`
- cwd：`resources/agent-core`
- PYTHONPATH 注入 `resources/agent-core/src`

缺任一关键文件时 fail-closed：`missing packaged Agent Core resource: ...`，不静默回退开发目录。

**已知限制（必须写进证据）：** 当前将开发机 `.venv` 原样打入安装包。这要求：

1. 在 Windows x64 上构建；
2. `.venv` 为 Windows 原生；
3. 发布证据记录 Python 版本与路径哈希；
4. 干净环境验收证明“无需系统 Python”。

后续可替换为 PyInstaller/standalone 分发，但本切片不切换工具链。

## 5. packaged 路径边界

| 组件 | packaged 路径 |
|------|----------------|
| Main | `resources/app.asar` 内 `dist-electron/main.js`（或 asar unpack 策略允许的路径） |
| preload | `dist-electron/preload.cjs`，与 Main 同目录解析 |
| Renderer | `dist/index.html` + assets，file:// 加载 |
| Agent Core | `resources/agent-core/**`（**必须 unpacked**，不可进 asar） |
| 用户数据 | `%APPDATA%/Bolt`（Electron app.getPath('userData')） |
| 工作区数据 | 用户选择的 workspace 内 `.bolt/`（卸载不删除） |

ASAR：

- 应用 JS/CSS 可进 asar
- `agent-core/.venv`、`python.exe`、native 扩展 **必须 asarUnpack / extraResources 外置**
- 现有 `extraResources` 已保证 Core 在 asar 外

## 6. Windows Credential Manager

安装版行为与开发版一致（P0 已验收）：

- API Key 只写入 Windows Credential Manager
- 禁止 DPAPI 文件 fallback 进入生产
- 旧 `.bolt/desktop-api-key` 原子迁移后删除明文
- 卸载：程序文件删除；Credential Manager 凭据默认保留（与“保留用户数据”一致），用户可在应用内删除 provider；证据记录该策略

## 7. 代码签名与时间戳

入口（已有）：

- `CSC_LINK`：证书路径或 base64（仅 env / CI secret）
- `CSC_KEY_PASSWORD`：仅 env / CI secret
- `.gitignore` 已忽略 `*.pfx *.p12 *.pem *.key`

本切片增加：

1. `scripts/verify-windows-signature.mjs`：对 EXE/安装包调用 `signtool verify /pa` 或记录 blocked
2. 时间戳服务器配置通过 electron-builder `win.rfc3161TimeStampServer`（公开 RFC3161），密码永不落盘
3. 无证书时：允许 unsigned 内部包；`release_signing_blocked=true`；玩家内测 Go = No

禁止：伪造签名、提交证书、日志打印密码。

## 8. 自动更新信任链

**当前策略基线：** 文档与决策写明 auto-update disabled。本切片实现**可测试的更新模块**，默认仍关闭生产自动检查。

设计：

```text
UpdateManifest (HTTPS only)
  version, channel, min_version, artifacts[{url, sha256, size}]
  signature (ed25519 over canonical JSON) OR detached checksum file with same trust root
Main UpdateService
  - 仅允许 allowlisted HTTPS host（构建时嵌入）
  - 拒绝任意用户配置更新 URL
  - 校验 version 单调（semver）；禁止不安全降级，除非 recovery flag
  - 下载到 temp；哈希/签名失败删除 temp；不覆盖当前安装
  - Core 忙（verified generation 有 active run 标记）时不强制
  - 安装失败保留旧版本；启动时选 last-known-good
```

无生产服务器：提供 `scripts/local-update-fixture-server.mjs` + 攻击夹具（坏签名、篡改、HTTP、错误 host）。生产更新链状态记 `production_update_channel_blocked` 直至真实 channel 就绪。

## 9. 更新失败回滚

1. 下载失败：保留当前安装，UI 提��，写本地诊断
2. 校验失败：删除 temp，拒绝安装
3. 安装失败：NSIS/ electron-updater 回滚到旧目录；应用可启动
4. 不允许静默降级到低于 `min_supported_version` 的包
5. 证据 check IDs：`update.success`、`update.reject-tamper`、`update.rollback`

## 10. 崩溃记录与用户反馈

范围：Renderer 崩溃、Main 崩溃、Agent Core 异常退出、启动失败、更新失败、安装失败。

本地诊断目录：`userData/diagnostics/`

| 文件 | 内容 |
|------|------|
| `crash-*.json` | 时间、组件、exitCode、脱敏 stack |
| `startup-*.json` | Core validationError / readiness 失败原因（无 secret） |
| `update-*.json` | 更新阶段与失败码 |

规则：

- 默认仅本地；上传必须用户主动同意
- 红action：API Key、Bearer、bootstrap secret、绝对用户路径、完整 prompt
- UI：复制脱敏诊断、打开日志目录、关闭收集开关
- 反馈入口不阻塞启动；反馈服务不可用时应用仍可用

实现落点：

- Main：`apps/desktop/electron/diagnosticsStore.ts` + 窄 IPC
- Renderer：设置中心「诊断与反馈」只读面板
- 不引入自动外发 crashReporter 上传

## 11. 日志脱敏与隐私

复用 `evidence_redactor` / 桌面侧同等规则：

- allowlist 字段输出
- path → role（`workspace` / `user_data` / `install_dir`）
- provider id → sha256(salt+id)
- 禁止 Authorization、api_key、token、私钥

## 12. 安装 / 升级 / 降级 / 卸载数据保留

| 数据 | 安装 | 升级 | 卸载 keep | 卸载 delete |
|------|------|------|-----------|-------------|
| 程序文件 | 写入 install_dir | 替换 | 删除 | 删除 |
| userData（设置/诊断） | 创建 | 迁移保留 | 保留 | 删除 |
| workspace `.bolt` | 不触碰 | 不触碰 | **永不随卸载删除** | 同左 |
| Credential Manager | 不预置 | 保留 | 默认保留 | 应用内可删；卸载脚本不批量 CredDelete |

NSIS：`oneClick: false`，可改安装目录。若 builder 无法提供卸载 keep/delete UI，默认 keep 并在 runbook 手测。

## 13. Release Evidence 格式

目录（gitignore，不提交敏感内容）：

```text
release-evidence/<version>-<commit>-<UTC>/
  manifest.json      # version, commit, channel, created_at_utc
  environment.json   # node/pnpm/python/electron 版本，OS（无用户名路径）
  artifacts.json     # 相对名、size、sha256
  checks.json        # id -> passed|failed|blocked|not_run
  events.ndjson      # 已脱敏事件
  sbom.json          # 依赖清单摘要
  logs/              # 可选脱敏日志
```

状态语义：任一 required check 为 `failed|blocked|not_run` ⇒ `release_status=failed`。  
`not_run` 与 `blocked` **绝不算通过**。

旧计划 check ID 保留并扩展：

```text
package.dir / package.portable / package.nsis
artifact.sha256 / artifact.sbom / artifact.secret-scan
signing.verify
install.nsis / startup.core / exit.no-child-process
update.success / update.reject-tamper / update.rollback
crash.redaction / diagnostics.copy
clean_windows_e2e
```

## 14. 玩家内测 vs 公开 Beta 门禁

| 条件 | 玩家小范围内测 | 公开 Beta |
|------|----------------|-----------|
| P0 安全 + UI 门禁 | 必须 | 必须 |
| 可重复打包 + 产物扫描 | 必须 | 必须 |
| 真实安装/启动/退出/卸载 | 必须 | 必须 |
| 代码签名 verify 通过 | 必须 | 必须 |
| 更新成功 + 篡改拒绝 + 回滚 | 必须（可用受控 channel） | 必须（生产 channel） |
| 崩溃脱敏 | 必须 | 必须 |
| 干净 Windows E2E | 必须 | 必须 |
| 真实模型最小调用证据 | 建议 | 必须 |
| 公开分发授权 | 用户书面授权 | 用户书面授权 |

**本 agent 永远不自行上传/公开发布。**

## 15. 架构数据流（packaged）

```text
Bolt.exe (Main)
  -> resolveAgentCoreRuntime(packaged=true, resourcesPath)
  -> spawn resources/agent-core/.venv/Scripts/python.exe -m bolt_core.desktop_runner
  -> readiness HMAC proof + strict /health
  -> verified generation {endpoint, bearer} 仅 Main 内存
  -> preload 窄 bridge（无 token/port/env）
  -> Renderer path-only client -> IPC transport -> Main fetch loopback
```

## 16. 8 维设计自审

| 维度 | 评级 | 结论 |
|------|------|------|
| 1. 安装包完整性 | 🟢 | SHA-256 + secret scan + runtime layout check |
| 2. 签名与更新供应链 | 🟡 | 无证书时诚实 blocked；更新模块默认关生产检查 |
| 3. Electron/Main/Renderer/Core 边界 | 🟢 | 沿用 P0；packaged 不回退 fetch/endpoint |
| 4. 凭据与日志脱敏 | 🟢 | CM-only + redaction allowlist |
| 5. 安装/更新/回滚/卸载一致性 | 🟢 | workspace 永不随卸载删；userData 显式策略 |
| 6. 干净环境可运行性 | 🟡 | 依赖打包 .venv；需 E2E 或 blocked + 脚本 |
| 7. 崩溃反馈隐私与恢复 | 🟢 | 本地默认、主动同意上传、不阻塞启动 |
| 8. 发布声明与证据一致 | 🟢 | not_run/blocked 不能当 passed |

Critical/Important 已写入设计：不伪造签名、不把本地 fixture 更新当生产完成、不把 dirty 开发启动当安装 E2E。

## 17. 实施顺序（摘要）

见 `docs/superpowers/plans/2026-07-11-windows-release-evidence.md`。

Task A 打包 hardening → B 安装验证脚本 → C 签名验证 → D 更新模块 → E 诊断 → F 产物扫描 → G 干净环境 → H Evidence 汇总。
