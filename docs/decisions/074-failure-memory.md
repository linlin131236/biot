# M74 Failure Memory — 设计决策

## 决策背景
Biot 在 M57/M60/M66/M67-M72 的 review gate 中积累了 P1/P2 修复记录，project-state 中也记录了已知风险。但这些信息散落在各个 markdown 文件中，无法结构化查询。M74 建立只读失败记忆索引，让 Agent 在遇到类似问题时能参考历史经验。

## 决策 1：从 review gates 静态提取
**选择**：解析 `docs/phase-*-review-gate.md` 中的 P1/P2 修复记录，构建 FailureRecord。

**理由**：
- P1/P2 修复是最有价值的失败经验
- review gates 已经有结构化格式
- 无需额外数据录入

## 决策 2：与 M64 FailureClassifier 对齐
**选择**：FailureRecord.category 使用 M64 的 8 个分类。

**理由**：
- 文档明确："与 M64 classifier 对齐，不直接自动修复"
- 保持分类体系一致性
- M65 SafeRetryLoop 依赖统一的分类体系

## 决策 3：不触发自动修复/自动重试
**选择**：API 只提供 GET，无 POST/PUT/DELETE。不暴露 auto_fix_possible。

**理由**：
- 文档明确："不直接自动修复"、"不自动重试危险工具"
- 失败记忆是参考信息，不是行动指令
- 修复决策仍需人工判断

## 决策 4：补充 project-state 风险
**选择**：同时索引 `docs/project-state.md` 中的已知风险，标记为 P3 严重度。

**理由**：
- 已知风险也是失败记忆的重要来源
- P3 标记区分于 review gate 中的 P1/P2 修复

## 风险
- P1/P2 提取依赖 review gate 格式的一致性；非标准格式可能遗漏
- 复发风险评估基于关键词匹配，未必精确
- 不索引 `failure_memory.py` 的运行时内存记录（重启丢失）
