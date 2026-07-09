# Bolt/Biot Project State

## 2026-07-09 二轮复审三项 Beta 阻断修复

- 当前阶段：M180 Desktop Beta Release Candidate 后的二轮复审修复。
- 本轮处理范围：只处理复审列为 Beta 发布前必须处理的 S2、S3、Q4，不进入新 milestone，不 push、不 release、不 tag、不 delete。
- S2 workspace lock：`resolve_app_workspace()` 无参数默认锁到当前工作区；模块级生产入口继续显式锁默认 workspace。测试/嵌入场景若要外部临时 workspace，必须显式传入自己的项目目录或显式关闭默认锁。
- S3 workspace 外写：`classify_path(..., operation="write")` 对 workspace 外路径改为 `level=6/action=deny`，与 patch 越界行为一致。
- Q4 fetchSkills：在 `/skills` 后端路由未接入前返回空列表，不再把未实现状态暴露成运行时 throw。
- P1 ContextCompressor：`budget` 参与 recent window 和 summary 选择；tool 结果超长内容会截断；极小 budget 下 AgentLoop 不再回退原始上下文，而是丢弃旧 plain 消息并记录 `has_summary`。
- D1 desktop runtime：`electron-builder.json` 将 `services/agent-core/.venv` 纳入 `extraResources`；静态 runtime 检查同时验证 `.venv/Scripts/python.exe` 源文件存在。
- 已新增/更新回归测试：workspace 默认锁、workspace 外写 deny、`fetchSkills()` 空列表 fallback、dogfood smoke fallback、budget-bounded summary、tool 截断、metadata=None、AgentLoop 极小 budget 不回退原文。
- 已验证：
  - `uv run pytest -q services/agent-core/tests/test_harness_workspace_lock.py services/agent-core/tests/test_risk.py`：23 passed。
  - `pnpm --filter @bolt/desktop test -- harnessClientAutonomy.test.ts dogfoodSmoke.test.ts`：56 files / 402 tests passed。
  - `uv run pytest -q services/agent-core/tests/test_context_compressor.py services/agent-core/tests/test_agent_loop_context_compression.py services/agent-core/tests/test_harness_workspace_lock.py services/agent-core/tests/test_risk.py`：51 passed。
  - `node scripts/check-desktop-package-runtime.mjs`：通过。
  - `pnpm run quality`：通过，shared 27 passed，desktop 402 passed，backend 1681 passed。
  - `git diff --check`：通过，仅 Windows LF/CRLF 提示。
- 仍未处理的近期项：当前旧 `win-unpacked` 产物尚未重新打包，需重新运行打包后再用 `--require-output` 验证 packaged Python runtime。

## 2026-07-09 第二轮全面审计修复状态

- 当前阶段：M180 Desktop Beta Release Candidate 后的第二轮审计修复。
- 代码修复提交：`7e47dae fix: harden second audit security and runtime findings`。
- 本轮修复来源：Claude / ZCodex / 八维度全面审核报告中的可验证问题。
- 修复范围：
  - Agent Core 本地认证代理从“只校验 localhost 主机”升级为“校验 localhost + 当前 Agent Core 端口”，降低 token 被转发到本机其他端口的风险。
  - Electron preload 继续只暴露受限 `agentCoreFetch`，不暴露明文 token；renderer 仍不直接访问 `ipcRenderer` / `fs` / `shell` / `process`。
  - 桌面启动时记录 Agent Core 实际端口，并通过 preload 只允许该端口走认证代理。
  - workspace lock 修正为：显式 `project_dir` / `BOLT_WORKSPACE` / 模块级生产入口会加锁；测试用 `create_app()` 不被当前仓库路径误锁。
  - `AgentLoop` 接入 `ContextCompressor`，只压缩普通 user/assistant 文本消息，保护 tool protocol 消息不被压坏。
  - 新增 `command_security` 专项测试，覆盖 shell 控制符、管道、重定向、命令替换和引号边界。
  - 打包 runtime smoke 增加 packaged Python runtime 检查；当前 `--require-output` 会正确 fail closed，因为正式 Python runtime 仍未打进 release 产物。
  - 前端与 Python 依赖从浮动版本收敛为当前可复现版本区间/精确版本，并更新 `pnpm-lock.yaml`。
- 已验证：
  - `uv run pytest services/agent-core/tests/test_harness_workspace_lock.py services/agent-core/tests/test_agent_loop.py services/agent-core/tests/test_agent_loop_context_compression.py services/agent-core/tests/test_agent_loop_messages.py services/agent-core/tests/test_command_security.py -q`：26 passed。
  - 失败回归组：43 passed。
  - `pnpm run quality`：通过；shared 27 passed，desktop 402 passed，backend 1673 passed。
  - `git diff --check`：通过，仅 Windows LF/CRLF 提示。
  - `node scripts/check-desktop-package-runtime.mjs`：通过。
  - `node scripts/check-desktop-package-runtime.mjs --require-output`：按预期 fail closed，提示缺少 `resources/agent-core/.venv/Scripts/python.exe`。
  - renderer 安全扫描：无新增真实暴露；命中均为注释或 Electron preload/main 允许边界。
- 未执行：未 push、未 release、未 tag、未 delete。
- 工作区注意：`.claude/` 仍为外部工具未跟踪目录，不提交。
- 剩余风险：
  - Windows release 产物仍需要真正嵌入 Python runtime；当前修复先把坏包从“静默通过”改成“明确阻断”。
  - `app.py` 仍是大型路由注册中心，后续可做低风险分域拆分，但本轮不擅自重构。

## 2026-07-09 zcodex 全量审查修复状态

- 当前阶段：M180 Desktop Beta Release Candidate 后的审查修复。
- 本轮修复提交：`6582237 fix: harden zcodex audit findings`。
- 质量门补强提交：`4cab104 chore: include backend tests in quality gate`。
- 修复范围：
  - Electron renderer 不再读取 Agent Core 明文 token，改由 preload 受限本机 fetch 代理添加认证。
  - 多个桌面面板不再直接使用 `window.fetch`，统一走父级注入 fetcher。
  - Planner node 状态更新从 POST 修正为 PATCH。
  - `/session-recovery` 返回真实结构化 recovery policy，不再吞掉不存在的 `get_policy()`。
  - checkpoint 创建/读取/恢复不再允许请求覆盖 workspace，恢复仍需用户明确确认。
  - 发布准备度与会话恢复面板按当前 shared/backend 字段展示，保留只读边界。
  - 根 pytest 配置补齐，`uv run pytest -q` 不再扫描桌面打包生成物。
  - `pnpm run quality` 纳入 `uv run pytest -q`，后续质量门不再漏掉 Python agent-core。
  - size gate 忽略 `release` 生成目录，避免 package smoke 产物污染质量门。
  - 首页“搜索 / 已安排”在真实功能接入前禁用，避免假按钮。
- 静态站同步修复：`D:\Bolt\bolt-cn-site\index.html` 的 CTA/footer 空 `<a>` 已补 `href`，该目录不是当前 Git 仓库。
- 已验证：
  - `uv run pytest -q`：1665 passed，2 warnings。
  - `pnpm run quality`：通过，shared 27 passed，desktop 401 passed，backend 1665 passed。
  - `pnpm --filter @bolt/desktop build`：通过。
  - `git diff --check`：通过，仅 Windows LF/CRLF 提示。
  - renderer 扫描：无 `window.fetch` 直连、无 `as any / unknown as`、无新增 `ipcRenderer/fs/shell/process` 暴露。
  - 静态站 `<a>` 无 href 扫描：OK。
- 未执行：未 push、未 release、未 tag、未 delete。
- 工作区注意：`.claude/` 仍为外部工具未跟踪目录，不提交；`apps/desktop/release/` 为打包生成物，不提交。

## 2026-07-09 打包 Smoke 修复状态

- 当前阶段：M180 Desktop Beta Release Candidate。
- 当前远端：`main = origin/main = 0d1e69c docs: mark M171-M180 pushed state`。
- 本轮修复：`apps/desktop/electron-builder.json` 增加 `electronDist: "node_modules/electron/dist"`，让 electron-builder 复用本地已安装 Electron 分发目录，不再在 packaging 阶段重复慢速下载 Electron zip。
- 已验证：`pnpm --filter @bolt/desktop package:win:dir` 通过，生成 `apps/desktop/release/win-unpacked/Bolt.exe`。
- 已验证：`node scripts/check-release-policy.mjs`、`node scripts/check-desktop-package-runtime.mjs --require-output`、`git diff --check` 通过。
- 未执行：未 push、未 release、未 tag、未 delete。
- 工作区：本轮配置/文档修复已提交：`f990c4e fix: reuse local electron distribution for desktop packaging`，待 push；`.claude/` 保持未跟踪、未提交。

## 当前稳定基线

- 当前分支：`main`
- 已完成到：M180 Desktop Beta Release Candidate
- 最新提交：`f38eae3 docs: mark M171-M180 local committed state`
- 远端基线：`origin/main = f38eae3 docs: mark M171-M180 local committed state`
- 分支状态：`main` 与 `origin/main` 已同步，无 ahead、无 behind
- 工作区状态：已跟踪文件干净；`.claude/` 为外部工具状态目录，保持未跟踪、未提交

## M171-M180 收口范围

- M171 Desktop Package Smoke：验证 build、Windows package、package runtime smoke 脚本存在。
- M172 First Run Setup：验证工作区、设置、权限中心入口存在。
- M173 Real Task Flow：验证补丁预览、安全测试、结果摘要和 dogfood smoke 链路存在。
- M174 Error State Experience：验证连接失败、模型失败、诊断中心等中文错误态可见。
- M175 Settings Readiness：验证设置持久化、API key 边界、设置页入口存在。
- M176 Audit Recovery Visuals：验证审计时间线、会话恢复和发布准备度入口存在。
- M177 Performance Quality Signals：验证质量门、桌面测试基线、构建基线存在。
- M178 Installer Readiness：验证 Windows 安装包脚本存在且 `--publish never`。
- M179 Desktop Dogfood Evidence：验证 dogfood 测试与 release dogfood 文档存在。
- M180 Desktop Beta Release Candidate：聚合 M171-M179，输出只读 Beta 候选结论。

## 本轮实现

- 新增 `DesktopBetaShipService`：只读聚合 M171-M180 桌面 Beta 发布候选门禁。
- 新增 `/desktop/beta-ship` API：返回 ready、checks、blockers、next_step。
- 新增 `DesktopBetaShipPanel`：桌面端中文展示发布候选状态，不提供 push/release/tag/delete 按钮。
- 新增 M171-M180 exec plan、decision、review gate 文档链。

## 最近验证

- `uv run pytest services/agent-core/tests/test_desktop_beta_ship.py -q`：5 passed
- `pnpm --filter @bolt/desktop test -- DesktopBetaShipPanel --run`：56 files / 399 tests passed
- `uv run pytest -q`：1662 passed
- `pnpm run quality`：通过（shared 27 passed，desktop 399 passed）
- `pnpm --filter @bolt/desktop build`：通过
- 真实仓库 `DesktopBetaShipService`：M171-M180 10/10 ready

## 已知风险

- M171-M180 当前是 release-candidate readiness gate，不自动打包、不自动发布。
- 真机安装包 smoke 仍需在人工授权下运行 `pnpm --filter @bolt/desktop package:win:dir`。
- `.claude/` 保持未跟踪、未提交。

## 硬规则

- 所有用户可见 UI 必须中文。
- 软件内不使用私人称呼，统一使用“用户 / 人工批准 / 用户确认”。
- 不自动 push、release、tag、delete。
- 不绕过 PermissionGate。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt/`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。

## 下一步

M171-M180 已 push 并同步。下一步建议在人工授权下运行 Windows `package:win:dir` 真机打包 smoke，确认可启动后再决定是否发布 Beta。
