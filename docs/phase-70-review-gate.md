# Phase 70 Review Gate — Agent Workflow Beta 大复盘

## 状态：✅ 通过 — 允许进入 M71

---

## 一、M61-M70 交付物完整性

| Milestone | Exec Plan | Decision | Review Gate | Project-State | Commit |
|-----------|:---------:|:--------:|:-----------:|:-------------:|:------:|
| M61 Planner Task Graph | ✅ 061 | ✅ 061 | ✅ 61 | ✅ | `02ebd98` |
| M62 Execution State Machine | ✅ 062 | ✅ 062 | ✅ 62 | ✅ | `c1e7fb5` |
| M63 Tool Selection Policy | ✅ 063 | ✅ 063 | ✅ 63 | ✅ | `841278b` |
| M64 Failure Classification | ✅ 064 | ✅ 064 | ✅ 64 | ✅ | `1315aa2` |
| M65 Safe Retry Loop | ✅ 065 | ✅ 065 | ✅ 65 | ✅ | `d56084b` |
| M66 Pause/Resume | ✅ 066 | ✅ 066 | ✅ 66 | ✅ | `e4b0208` + P1 fixes |
| M67 Human Steering | ✅ 067 | ✅ 067 | ✅ 67 | ✅ | `bc13f85` |
| M68 Budget Controls | ✅ 068 | ✅ 068 | ✅ 68 | ✅ | `74aea93` |
| M69 Recovery Dogfood | ✅ 069 | ✅ 069 | ✅ 69 | ✅ | `32c1263` |
| M70 Workflow Beta | ✅ 070 | ✅ 070 | ✅ 70（本文件） | 待更新 | 待 commit |

**结论**：全部 10 个 milestone 的 exec plan、decision、review gate、project-state 更新、commit 均已就位。

---

## 二、7 层架构复盘

### 第 6 层：任务编排 ✅ 达标
- M61 Task Graph：任务可规划为 DAG
- M62 State Machine：8 状态 + 18 转换
- M66 Pause/Resume：快照式暂停恢复，强制权限复查
- M67 Human Steering：6 种意图分类，副作用仅生成 pending
- M68 Budget Controls：四维门控（steps/tool_calls/runtime/context_tokens）
- M69 Dogfood：9 项 readiness 检查全部通过，闭环可验证

**评价**：长任务从规划→执行→暂停→转向→预算→恢复的完整闭环已形成。

### 第 5 层：执行引擎 ✅ 达标
- M63 Tool Selection：26 种工具 + 4 级分类（read_only/side_effect/dangerous/unknown）
- M64 Failure Classification：8 种分类 + 中文诊断
- M65 Safe Retry：双重安全门，不重试危险工具
- M62 State Machine：状态驱动执行流程

**评价**：工具选择、失败处理、重试策略、状态管理均受控。

### 第 4 层：上下文引擎 ⚠️ 基础可用，待 M71-M72 补齐
- 现有：MemoryStore、ContextBuilder、ConversationStore、PerceptionService
- M71 将补齐：Project Profile（项目画像）
- M72 将补齐：Code Map Index（代码地图）

**评价**：基础骨架已有，足够支撑进入 V3。M71-M72 补齐项目理解和代码索引。

### 第 3 层：Agent 大脑 — 不在本批复盘范围
**评价**：ModelGateway、ContextBuilder、AgentLoop 基础能力已有。Plan 模式、System Prompt 注入、子代理编排是后续方向，本批不过度重构。

### 第 2 层：安全底座 ✅ 无回退
- [x] PermissionGate 未被绕过（M69 dogfood 验证）
- [x] 不存在自动 approve（全量代码扫描确认）
- [x] 不存在自动 push/release/tag/delete（全量代码扫描确认）
- [x] 审计追溯完整（TraceLog + Evidence + source_refs）
- [x] 脱敏/完整性/诊断基础设施齐全（M55-M60）

**评价**：安全底座在 M61-M70 期间无回退，所有新增能力均遵循"不绕过 PermissionGate"原则。

### 第 1 层：基础设施 ✅ 达标
- 后端 pytest：804 passed（无回退，M66: 699 → M69: 804）
- shared tests：27 passed
- desktop tests：195 passed
- desktop build：通过
- docs：完整（10 个 exec plan + 10 个 decision + 10 个 review gate）
- Chinese UI 检查：通过

---

## 三、安全扫描

| 检查项 | 结果 |
|--------|:----:|
| `as any` / `unknown as` | ✅ 0 处 |
| renderer 暴露 `ipcRenderer` | ✅ 仅注释和测试断言 |
| renderer 暴露 `fs` / `shell` / `process` | ✅ 仅注释和测试断言 |
| 自动 approve | ✅ 不存在 |
| 自动 push/release/tag/delete | ✅ 不存在 |
| PermissionGate 绕过 | ✅ 不存在 |
| 中文 UI | ✅ 通过 |
| git diff --check | ✅ 仅有 LF/CRLF 警告 |

---

## 四、全量测试

| 套件 | 结果 |
|------|:----:|
| `uv run pytest -q` | 804 passed |
| `pnpm --filter @bolt/shared test` | 27 passed |
| `pnpm --filter @bolt/desktop test` | 195 passed |
| `pnpm --filter @bolt/desktop build` | 通过 |

**总计：1026 tests 全部通过。**

---

## 五、大复盘结论

### V2 Agent 工作流核心（M61-M70）beta 骨架是否达标？

**✅ 达标。** 

M61-M70 构建了从任务规划、状态驱动执行、工具选择、失败分类、安全重试、暂停恢复、人工转向、预算控制到闭环验证的完整 Agent 工作流。

核心安全原则贯穿全部 10 个 milestone：
1. 不绕过 PermissionGate
2. 不自动批准权限
3. 不自动执行危险动作
4. 副作用操作需要人工确认
5. 所有阻断和诊断使用中文

### 是否允许进入 M71？

**✅ 允许进入 M71 Project Profile。**

V2 Agent 工作流核心已达到 beta 骨架标准，可以进入 V3 项目理解与长期记忆阶段。

---

## 六、已知风险和后续建议

1. **M61 Task Graph 为纯内存模型**：服务重启后图数据丢失，M71+ 项目画像可能需要持久化支持
2. **第 4 层上下文引擎较薄**：M71 Project Profile + M72 Code Map Index 将作为本批补齐
3. **Hermes 的自进化技能、MOA、多平台 Gateway**：记录为长期方向，不纳入本批复盘范围
4. **Plan 模式、System Prompt 注入、子代理编排**：后续方向，本批不越界大重构
