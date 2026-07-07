# M104 Decision — Read-only Tool Runner 只读工具运行器

## 决策
新建 `ReadOnlyToolRunner` 类，包装 PathGuard + ToolRegistry + 输出脱敏 + 审计，不复用现有 `ReadOnlyToolExecutor`。

## 理由
1. 现有 `ReadOnlyToolExecutor` 按 ToolRequest 协议工作，与 ToolRegistry 不集成
2. M104 需要 Registry 验证（只执行已注册的 read_only 工具）、安全路径检查、输出脱敏、审计追踪
3. 独立的 Runner 更聚焦、更易测试

## 安全设计
- **四层阻断**：Registry 类别检查 → PathGuard 路径验证 → 扩展阻断 (.claude/ 等) → 输出脱敏
- **路径安全**：继承 PathGuard（防穿越 + 防 secret），额外阻断 .claude/、node_modules 等
- **输出脱敏**：按行检测敏感键名（api_key, secret, token 等）和值模式（Bearer, sk-, ghp_ 等）
- **Git 安全**：仅允许只读 git 命令（status, log, diff --stat），不允许 push/commit
- **全部审计**：每次执行产出 audit record，包含 step、result、reason

## 支持的操作
- `read_file`：读文件（安全路径 + 脱敏）
- `list_dir`：列目录（隐藏被阻断的目录）
- `git_status`：git status --short --branch
- `git_log`：git log --oneline（最多 50 条）
- `git_diff_summary`：git diff --stat
- `query_docs`：列出 docs 目录 .md 文件
- `query_tests`：列出测试文件（按 pattern）

## 测试覆盖
- 26 tests：读文件 (8)，列目录 (3)，注册表检查 (3)，query_docs (2)，query_tests (2)，Git (2)，不支持操作 (1)，审计 (2)
