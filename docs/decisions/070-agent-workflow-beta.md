# M70 Agent Workflow Beta — 设计决策

## 决策：docs-only review gate
**选择**：M70 不新增代码，以只读 review gate 形式做大复盘。

**理由**：
- 文档明确："可以是只读 readiness service/API，也可以 docs-only review gate，但必须可验证"
- M61-M69 已有 804 个测试覆盖所有功能点
- 复盘的重点是"这些能力是否形成闭环"，不是"再加一个功能"
- 安全扫描和交付物检查均为自动化可验证

## 7 层架构复盘结论

### 第 6 层：任务编排 ✅
M61-M69 形成长任务闭环：
- M61 Task Graph → 任务可规划
- M62 State Machine → 执行有状态
- M66 Pause/Resume → 可暂停恢复
- M67 Human Steering → 可人工转向
- M68 Budget Controls → 有预算限制
- M69 Dogfood → 闭环可验证

### 第 5 层：执行引擎 ✅
- M63 Tool Selection → 工具选择策略
- M64 Failure Classification → 失败分类
- M65 Safe Retry → 安全重试
- M62 State Machine → 状态驱动

### 第 4 层：上下文引擎 ⚠️
现有 MemoryStore + ContextBuilder + ConversationStore 提供基础能力。M71-M72 将补齐 Project Profile 和 Code Map Index。

### 第 2 层：安全底座 ✅
- PermissionGate：未绕过
- 自动 approve：不存在
- 自动 push/release/tag/delete：不存在
- 审计追溯：完整

### 第 1 层：基础设施 ✅
- 804 后端测试
- 27 shared 测试
- 195 desktop 测试
- desktop build 通过
- docs 完整

## 是否允许进入 M71
**✅ 允许。** V2 Agent 工作流核心 beta 骨架达标。
