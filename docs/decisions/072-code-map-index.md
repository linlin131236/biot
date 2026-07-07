# M72 Code Map Index — 设计决策

## 决策背景
Agent 需要理解项目代码结构才能有效工作。但全量加载代码到上下文是不现实的。CodeMap 提供轻量索引——Agent 先查地图，再按需读取具体文件。

## 决策 1：静态解析，不 import
**选择**：Python 文件用 `ast.parse()` 静态提取符号，TS 文件用正则匹配 exports/functions。

**理由**：
- 文档明确："不执行代码，不 import 项目模块来反射"
- 静态解析安全、快速、无副作用
- `ast.parse()` 是标准库，无额外依赖
- 解析失败时优雅降级（SyntaxError 静默跳过）

## 决策 2：限制索引范围
**选择**：只索引 4 个核心目录，排除 node_modules/dist/build/缓存/venv/.bolt/secret。

**理由**：
- 文档明确索引范围
- 全项目索引代价大且无意义（大量依赖代码）
- 核心目录覆盖 90% 的 Agent 需要理解的文件

## 决策 3：风险提示（risk_hints）
**选择**：每项索引扫描关键词（permission, shell, subprocess, file.write, ipcRenderer 等），标记潜在风险文件。

**理由**：
- 让 Agent 在读取文件前就能感知风险
- 不阻止读取，仅提示——是上下文增强，不是安全门控
- 安全门控仍由 PermissionGate 负责

## 决策 4：disclaimer 端点
**选择**：提供 `GET /code-map/disclaimer` 明确声明"代码地图只是只读上下文，不授予执行权限"。

**理由**：
- 满足验收标准中的明确要求
- 防止 Agent 误以为 CodeMap 索引 = 执行授权

## 风险
- AST 解析对大文件可能有性能开销（已设 500KB 上限）
- TS 正则提取不如 AST 精确（但安全且无依赖）
