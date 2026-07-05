# Phase 1-3 Review Gate 报告

> 生成时间: 2026-07-06
> 基线: origin/main (0c79975)
> 本地 commits: 3 (未 push)

---

## 1. Git 状态

```
## main...origin/main [ahead 3]
 M docs/agent-run-log.md (未提交的日志更新)
```

## 2. 本地 Commits

| Commit | Message | 文件数 | 增/删 |
|--------|---------|--------|-------|
| f2a65ee | feat: add real llm provider foundation | 13 | +558 / -91 |
| 57fe76f | feat: expand core coding tools | 19 | +888 / -18 |
| 5cc269c | feat: add persistent goal mode | 11 | +774 / -1 |
| **合计** | | **35 unique** | **+2216 / -106** |

### f2a65ee 文件范围
```
docs/agent-run-log.md                    |  44 +++++++
services/agent-core/pyproject.toml       |   3 +-
services/agent-core/src/bolt_core/agent_loop.py    |  43 +++---
services/agent-core/src/bolt_core/model_gateway.py | 129 +++++++++++-------
services/agent-core/src/bolt_core/model_settings.py|   3 +-
services/agent-core/src/bolt_core/planner.py       |  31 ++++-
services/agent-core/src/bolt_core/provider_registry.py | 56 +++++++++
services/agent-core/src/bolt_core/tool_schemas.py  | 109 ++++++++++++++++
services/agent-core/tests/test_agent_loop.py       |  48 +++---
services/agent-core/tests/test_model_gateway.py    |  57 ++++++--
services/agent-core/tests/test_planner.py          |  17 ++-
services/agent-core/tests/test_provider_registry.py|  64 ++++++++++
services/agent-core/tests/test_tool_schemas.py     |  45 +++++++
```

### 57fe76f 文件范围
```
docs/agent-run-log.md                    |  15 ++++
packages/shared/src/protocol.ts          |  36 ++++++
scripts/check-architecture.mjs          |   2 +-
services/agent-core/src/bolt_core/agent_loop.py    |  13 +-
services/agent-core/src/bolt_core/app.py           |  16 ++++
services/agent-core/src/bolt_core/background_executor.py | 102 ++++++++++++++++
services/agent-core/src/bolt_core/harness.py       |  87 ++++++++++++-
services/agent-core/src/bolt_core/permission_gate.py|  30 +++--
services/agent-core/src/bolt_core/risk.py          |  24 +++-
services/agent-core/src/bolt_core/tool_executor.py |  25 +++-
services/agent-core/src/bolt_core/tool_schemas.py  | 137 +++++++++++++++++++-
services/agent-core/src/bolt_core/web_tools.py      |  77 ++++++++++++
services/agent-core/tests/test_background_executor.py | 71 ++++++++++
services/agent-core/tests/test_file_patch.py        |  64 ++++++++++
services/agent-core/tests/test_permission_gate.py   |  70 ++++++++++
services/agent-core/tests/test_risk.py              |  55 ++++++-
services/agent-core/tests/test_tool_executor.py     |   4 +-
services/agent-core/tests/test_tool_schemas.py      |  27 ++++
services/agent-core/tests/test_web_tools.py         |  51 +++++++
```

### 5cc269c 文件范围
```
docs/agent-run-log.md                    |  83 ++++++++++++
scripts/check-architecture.mjs          |   2 +-
services/agent-core/src/bolt_core/app.py           |  32 +++++
services/agent-core/src/bolt_core/evidence.py      |  31 +++++
services/agent-core/src/bolt_core/goal.py          | 151 ++++++++++++++++++++++
services/agent-core/src/bolt_core/goal_runner.py   |  61 +++++++++
services/agent-core/src/bolt_core/goal_service.py  |  98 ++++++++++++++
services/agent-core/src/bolt_core/harness.py       |   3 +
services/agent-core/tests/test_evidence.py         |  50 +++++++
services/agent-core/tests/test_goal.py             | 117 ++++++++++++++++
services/agent-core/tests/test_goal_runner.py      | 147 ++++++++++++++++++++++
```

## 3. 验证结果

| 验证项 | 结果 |
|--------|------|
| Python pytest (213 tests) | ✅ 全部通过 (7.72s) |
| pnpm quality (6 lint gates + 2 vitest suites) | ✅ 全部通过 |
| pnpm --filter @bolt/desktop build | ✅ 构建成功 (344ms) |
| git diff --check | ✅ 无空白错误 |

---

## 4. 七项风险专项评估

### 4.1 check-architecture.mjs 白名单新增是否可避免

**结论：不可完全避免，但可优化。**

原始白名单 4 个文件（harness.py, file_writer.py, patch_engine.py, shell_executor.py），新增 2 个：

| 文件 | 使用原因 | 合理性 |
|------|---------|--------|
| `background_executor.py` | subprocess 管理后台进程，功能等同于 shell_executor.py 的异步变体 | ✅ 合理 |
| `goal.py` | GoalPersistence.save() 使用 write_text 写 JSON 元数据文件 | 🟡 可优化 |

**优化建议：** 把 GoalPersistence 从 goal.py 拆成独立文件 `goal_persistence.py`，使 goal.py 纯数据+构建器，不用 write_text，自然不需要白名单。目标：白名单只扩展 1 个（background_executor），goal.py 的白名单是拆分不够导致的。

---

### 4.2 background_executor.py 进程泄漏 / kill 超时 / stdout 堆积

| 风险 | 评估 | 严重度 |
|------|------|--------|
| **进程泄漏** | `_processes` dict 持有 Popen 引用。kill() 时 pop 移除 ✅，但 poll() 检测到进程完成后不移除。已完成的进程引用永远留在 dict 里。 | 🟡 中 |
| **kill 超时** | terminate() + wait(timeout=5)，超时后 kill()。逻辑正确，但极端情况 kill() 也失败则变僵尸。 | 🟢 低 |
| **stdout 管道死锁** | 🔴 **最危险**。stdout=PIPE + stderr=STDOUT，但只在 poll/kill 时调用 _collect_output。如果长时间不 poll（例如用户忘了），stdout 管道缓冲区满（~64KB），进程 write() 阻塞，整个子进程挂死。 | 🔴 高 |
| **输出堆积** | _output dict 无大小上限，长时间运行的进程输出可能吃光内存。 | 🟡 中 |

**修复建议：**
1. 用后台线程持续消费 stdout（Thread + readline），避免管道死锁
2. poll() 检测到 retcode != None 后 pop 进程引用，加 completed 状态缓存
3. 加 max_output_size（如 1MB），超限截断

---

### 4.3 goal.py / GoalRunner 是否严格执行 budget

| 预算类型 | 检查位置 | 正确性 | 问题 |
|----------|---------|--------|------|
| max_steps | 循环开头 `step_num > goal.max_steps` | 🟡 | step_count 永远是 0（with_step() 存在但未调用），传入已有 step_count 的 goal 语义不清 |
| max_cost | 循环开头 `total_cost >= goal.max_cost` | 🟡 | cost 只在 step_result 返回 "cost" key 时累加。step_fn 忘记返回 cost → total_cost 永远 0 → max_cost 形同虚设 |
| max_wall_time | 循环开头 + 循环末尾双重检查 | ✅ | 正确 |

**额外问题：**
- **failed 步骤无限循环**：step 返回 "failed" 状态时直接 `continue`，没有连续失败计数器。同一个问题反复失败不会触发停止。
- **step_count 不更新**：GoalRunner 不调用 goal.with_step()，goal.step_count 始终为初始值。

**修复建议：**
1. 加 `consecutive_failures` 计数器，≥3 则返回 GoalStatus.FAILED
2. 每步默认最小 cost（如 0.01），避免 cost 永远为 0
3. step_num 独立计数，不依赖 goal.step_count
4. 每步结束后调用 goal = goal.with_step(step_num)

---

### 4.4 EvidenceLog 是否存在用 "pass" 字符串误判完成的问题

**当前问题代码（goal_runner.py 第 56-57 行）：**

```python
if not self._completion_check_fn and step_result.get("evidence_type"):
    return GoalRunnerResult(GoalStatus.COMPLETED, "criteria met with evidence", step_num)
```

**含义：** 如果没有提供 completion_check_fn，任何带有 `evidence_type` key 的成功步骤都判定为 COMPLETED。一个 tool call 返回 `{"evidence_type": "file_read"}` 就算完成，完全不管 criteria 是什么。

**这是 Phase 3 最大的设计缺陷。** 完成判定不应该有默认的宽松模式。

**修复建议：**
1. 移除默认的 evidence_type 判定逻辑
2. 没有提供 completion_check_fn → 永不自动完成，只靠 budget 停止
3. 或提供内置的 CriteriaCompletionChecker：逐条 criteria 检查 evidence 是否覆盖
4. 绝不能靠字符串匹配（"pass" in output）判定完成

---

### 4.5 protocol.ts 重写是否影响 desktop 兼容

**改动范围：** protocol.ts 从 ~180 行扩展到 ~220 行，新增类型：
- `FilePatchPayload`, `TerminalSpawnPayload`, `TerminalPollPayload`, `TerminalKillPayload`
- `WebSearchPayload`, `WebExtractPayload`, `BackgroundProcess`

| 检查项 | 结果 |
|--------|------|
| 原有类型保持不变 | ✅ HarnessRun, ToolRequest, ToolResult, PendingPermission 等全部保留 |
| type guards 未修改 | ✅ isHarnessRun, isToolRequest, isMemorySnapshot 正常 |
| shared vitest 测试 | ✅ 11/11 通过 |
| desktop vitest 测试 | ✅ 50/50 通过 (8 文件) |
| TypeScript 编译 | ✅ build 通过 |

**结论：** 向后兼容，新增类型不破坏现有代码。但 desktop 端还没有消费新类型（/goals API 等），Phase 5 需要同步更新。

---

### 4.6 harness.py 是否超过或接近 size gate

| 文件 | 行数 | 上限 (300) | 余量 |
|------|------|-----------|------|
| harness.py | **295** | 300 | **5 行** 🔴 |
| app.py | 177 | 300 | 123 行 |
| goal.py | 151 | 300 | 149 行 |
| goal_service.py | 98 | 300 | 202 行 |

**harness.py 只剩 5 行余量。** Phase 4 往 harness 里加任何逻辑都会超标。

**修复建议：** Phase 4 开始前先把 harness.py 中的 terminal 相关方法拆到 TerminalService：
- `terminal_list()`, `terminal_poll()`, `terminal_kill()`, `terminal_output()`
- `_execute_terminal()`
- 预计可减 40-50 行

---

### 4.7 Goal API 持久化冲突和并发写入风险

**当前设计：**
- 存储：`workspace/.bolt/goals/{goal_id}.json`，每个 goal 独立文件
- 写入：直接 `write_text()`，无锁无原子性
- 读取：直接 `read_text()`，无错误处理

| 风险 | 评估 | 严重度 |
|------|------|--------|
| **goal_id 路径遍历** | 🔴 **安全漏洞**。load() 不验证 goal_id 格式，传入 `../../etc/passwd` 可读任意文件。 | 🔴 高 |
| **并发写入** | 单进程 FastAPI + asyncio，但两个请求同时 save 同一个 goal_id，文件可能写坏。 | 🟡 中 |
| **进程崩溃丢数据** | write_text 不是原子操作（先清空再写），崩溃可能丢文件。 | 🟡 中 |
| **JSON 解析失败** | load() 无 try-except，损坏的 JSON 文件导致 500。 | 🟡 中 |
| **goal_id 碰撞** | uuid4 hex[:8] = 32 bit，碰撞概率 ~1/4B。单机场景 OK。 | 🟢 低 |

**修复建议：**
1. 🔴 **最高优先级**：goal_id 输入验证，必须匹配 `^goal_[a-f0-9]{8}$`
2. save() 使用 write-to-temp + rename 原子写入
3. load() 加 try-except，返回 None 或抛专用异常
4. 并发写入加 threading.Lock（单进程够用）

---

## 5. 风险汇总

### 🔴 阻塞 Phase 4（建议先修）

| # | 问题 | 严重度 | 修复量 |
|---|------|--------|--------|
| 1 | background_executor stdout 管道死锁 | 高 | ~30 行（后台线程消费） |
| 2 | goal_id 路径遍历漏洞 | 高 | ~5 行（输入验证） |
| 3 | GoalRunner 默认完成判定太宽松 | 高 | ~15 行（移除默认判定） |
| 4 | harness.py 仅 5 行余量 | 高 | ~50 行拆分 |

### 🟡 不阻塞但需后续处理

| # | 问题 | Phase |
|---|------|-------|
| 5 | GoalRunner consecutive_failures 计数器 | 4 |
| 6 | GoalRunner step_count 不更新 | 4 |
| 7 | GoalPersistence 原子写入 | 4 |
| 8 | GoalPersistence 从 goal.py 拆出 | 4 |
| 9 | poll() 不移除已完成进程引用 | 4 |
| 10 | _output 无大小上限 | 6 |

---

## 6. 爸爸需要做的决定

1. **是否先修 4 个 🔴 阻塞项再进 Phase 4？**
   - 修 → 需要额外 1 个 commit（fix: address phase 1-3 review gate findings）
   - 不修 → 带着已知问题继续，Phase 4 一并处理

2. **check-architecture.mjs 白名单策略：**
   - A: 保持现状（6 个白名单文件）
   - B: 拆 goal.py 为 goal.py + goal_persistence.py，白名单只加 background_executor

3. **GoalRunner 默认完成判定：**
   - A: 移除默认判定，没有 completion_check_fn 则只靠 budget 停止
   - B: 提供内置 CriteriaCompletionChecker
   - C: 保持现状但加 WARNING 日志
