# Bolt Task 2 Secret P0 Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关闭 Task 2 SQLite 持久化的 Secret 绕过路径，并用磁盘 canary 证明被拒绝的 Secret 不进入数据库、WAL、SHM、备份、日志或异常。

**Architecture:** 在 `persistence/models.py` 建立统一递归 SecretBoundary 与 URL/文本字段验证；`ControlPlaneRepository` 的每个持久化入口在事务前调用它。新增 message/checkpoint 基础 Repository 方法只覆盖数据层，不接入 Harness。

**Tech Stack:** Python 3.12、SQLite、pytest、urllib.parse、unicodedata、正则表达式。

---

### Task 1: Secret 绕过 RED 测试

**Files:**
- Modify: `services/agent-core/tests/test_persistence_repositories.py`

- [ ] **Step 1: 添加敏感 key/value 参数化测试**

测试值必须包含 `apiKey`、`x-api-key`、`password`、`headers.Cookie`、`privateKey`、URL query `access_token`、私钥头和常见赋值形式；断言 `create_task` 抛出不含 canary 的 `ValueError`。

- [ ] **Step 2: 添加四类 JSON 字段测试**

用相同 canary 分别调用 task、runtime event、message metadata、checkpoint payload 写入口；缺失的方法应产生预期 RED。

- [ ] **Step 3: 添加 model profile 直接文本列测试**

分别测试 `save_model_profile` 与 `update_model_profile` 拒绝含 userinfo、敏感 query 和 fragment 的 `base_url`。

- [ ] **Step 4: 添加磁盘 canary 测试**

拒绝写入后创建 backup，扫描 `bolt.sqlite3`、`-wal`、`-shm` 与 `backups/*.sqlite3`；断言均不含 canary。

- [ ] **Step 5: 运行 RED**

Run:

```powershell
uv run --project services/agent-core pytest services/agent-core/tests/test_persistence_repositories.py -q
```

Expected: 新增绕过测试失败，旧测试继续通过；失败原因是当前验证器接受输入或 Repository 方法缺失。

### Task 2: 统一 SecretBoundary 最小实现

**Files:**
- Modify: `services/agent-core/src/bolt_core/persistence/models.py`
- Modify: `services/agent-core/src/bolt_core/persistence/repositories.py`
- Test: `services/agent-core/tests/test_persistence_repositories.py`

- [ ] **Step 1: 实现键名规范化和敏感键族判断**

使用 NFKC、`casefold()` 与字母数字过滤生成规范键；精确阻断 Token 族，子串阻断 password/secret/credential/apiKey/privateKey/authorization/cookie/header 等强敏感族，同时允许 `token_count` 等非凭据计数字段。

- [ ] **Step 2: 实现非回显的字符串 Secret 检测**

检测 NUL、Authorization、私钥头、常见凭据前缀和敏感赋值格式；错误只返回固定类别消息。

- [ ] **Step 3: 实现 URL 专用验证**

通过 `urlsplit`/`parse_qsl` 验证 `http`/`https`、host、userinfo、query key、fragment、长度和控制字符。

- [ ] **Step 4: 覆盖 Repository 全写入口**

在事务前验证 JSON 和直接文本；新增 `append_message` 与 `save_checkpoint`，二者都调用 `validate_json_object`。

- [ ] **Step 5: 运行 GREEN**

Run:

```powershell
uv run --project services/agent-core pytest services/agent-core/tests/test_persistence_repositories.py -q
```

Expected: 该文件全部通过，且没有 warning/error。

### Task 2A: 第三次失败后的字段级 SecretPolicy 重设计

**Files:**
- Modify: `services/agent-core/tests/test_persistence_repositories.py`
- Modify: `services/agent-core/src/bolt_core/persistence/models.py`
- Modify: `services/agent-core/src/bolt_core/persistence/repositories.py`

- [ ] **Step 1: 写第三轮架构 RED**

新增真实 Repository/SQLite 测试：`token_value`/`tokenValue` 拒绝；`token_count`/`max_tokens` 允许；编码 userinfo、多层编码 query key、空格 host 拒绝；`Basic configuration guide` 与 `basic principles only` message 允许。运行单文件并确认因现有通用启发式失败。

- [ ] **Step 2: 将通用文本验证拆成字段级策略**

实现 workspace path、identifier、message content、credential reference、JSON value、HTTP URL 六个明确入口。Repository 必须在每个字段调用对应策略，不能继续复用单一通用扫描函数。

- [ ] **Step 3: 建立 Token usage 明确允许规则**

规范 key 只要包含 `token` 默认拒绝；仅允许明确 usage/计数字段。禁止通过 endswith、startswith 或继续扩充 Token 黑名单解决。

- [ ] **Step 4: URL 编码 fail closed**

`netloc` 和 raw query key 只要包含 `%` 就拒绝；不得继续增加 `unquote` 轮数。验证 scheme、hostname/IP、DNS label、userinfo、fragment、控制字符、空白和端口。

- [ ] **Step 5: 结构化 Basic/Bearer**

仅拒绝完整 `Basic|Bearer <single-token>` 值或 Authorization assignment/header；允许包含 Basic/Bearer 单词的普通句子。

- [ ] **Step 6: 运行 GREEN 与 focused**

```powershell
uv run --project services/agent-core pytest services/agent-core/tests/test_persistence_repositories.py -q
uv run --project services/agent-core pytest services/agent-core/tests/test_persistence_database.py services/agent-core/tests/test_persistence_migrations.py services/agent-core/tests/test_persistence_repositories.py services/agent-core/tests/test_persistence_app_injection.py -q
```

Expected: 全部退出码 0；合法文本用例与拒绝用例同时通过。

### Task 3: Task 2 focused 与静态门禁

**Files:**
- Verify only; no new production scope.

- [ ] **Step 1: 运行 Task 2 focused**

```powershell
uv run --project services/agent-core pytest services/agent-core/tests/test_persistence_database.py services/agent-core/tests/test_persistence_migrations.py services/agent-core/tests/test_persistence_repositories.py services/agent-core/tests/test_persistence_app_injection.py -q
```

- [ ] **Step 2: 编译与架构门禁**

```powershell
uv run --project services/agent-core python -m compileall -q services/agent-core/src/bolt_core/persistence
node scripts/check-architecture.mjs
git diff --check
```

Expected: 全部退出码 0。

### Task 4: 独立双重审查

**Files:**
- Review all Task 2 diffs.

- [ ] **Step 1: 规格审查**

核对 Task 2 任务书、设计文档与测试矩阵；禁止把 Task 4 业务接线当成 Task 2 实现。

- [ ] **Step 2: 代码质量与攻击审查**

攻击大小写、分隔符、camelCase、Unicode 兼容字符、嵌套/list、URL 编码、重复 query、userinfo、异常回显、WAL/backup 与 update 路径。

- [ ] **Step 3: 修复所有 P0/P1 并重新审查**

每项修复必须新增 RED，确认失败后再改生产代码；Reviewer 未明确通过前不得进入全量验收。

### Task 5: 全量验收

**Files:**
- Verify only.

- [ ] **Step 1: 后端全量**

```powershell
uv run --project services/agent-core pytest -q
```

- [ ] **Step 2: Desktop 全量与构建**

```powershell
pnpm --filter @bolt/desktop test -- --run
pnpm --filter @bolt/desktop build
```

- [ ] **Step 3: 最终差异与 Secret 证据**

```powershell
node scripts/check-architecture.mjs
git diff --check
git status --short
```

Expected: 所有命令有完整最终汇总；若超时或偶发失败，记录真实状态并独立归因，不得宣布完成。

### Task 6: 交付门禁

- [ ] **Step 1: 对抗式终审**

输出架构、身份、凭据、隔离、并发、一致性、真实性和发布八维红黄绿结论。

- [ ] **Step 2: 提交决策**

只有 focused、全量、构建、架构、磁盘 canary 和独立双审全部通过，才允许只暂存 Task 2 文件并提交；否则保持未提交并报告 No-Go。无论结果如何，Task 3 都不在本计划内启动。
