# M71 Project Profile — 设计决策

## 决策背景
V2 Agent 工作流核心（M61-M70）已通过 beta 骨架验收。进入 V3 阶段，首要任务是让新窗口/新 Agent 能稳定理解项目上下文，不再每次从零开始。

## 决策 1：静态文件提取，不依赖运行中 Agent
**选择**：从 docs/project-state.md、git HEAD、pyproject.toml/package.json 等静态文件提取信息。

**理由**：
- 可在任意时刻运行，不依赖 Agent 状态
- 确定性输出，不引入 LLM 推理
- 对齐 Context Lakehouse 原则：source_refs 永远是原始文件路径

## 决策 2：不读 secret / 证书材料
**选择**：`_is_safe_path()` 排除 .env、credentials、证书、私钥等文件。

**理由**：
- 文档明确："不读 secret，不读证书材料"
- Profile 是上下文入口，不应承载敏感信息
- 对齐安全底座审计原则

## 决策 3：缺失降级，不崩溃
**选择**：所有 `_read_doc` 和 `_extract_*` 方法在文件缺失时返回中文降级说明。

**理由**：
- 项目可能处于不同完成度，文档不一定齐全
- Profile 是辅助工具，不应因缺失文档而导致流程中断

## 风险
- Profile 精度依赖 project-state.md 维护质量
- 技术栈检测较浅（仅看配置文件存在性），不深入版本/依赖细节
