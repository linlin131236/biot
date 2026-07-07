# M104 Exec Plan — Read-only Tool Runner 只读工具运行器

## 目标
实现第一类真正可用的安全工具运行器，但仅限只读工具。

## 参考资料
- Phase13 深度笔记 — 纯工具 vs 有副作用工具，Circuit Breakers
- Agent开发技术栈 — FC原子能力单一职责

## 设计

### ReadOnlyToolRunner
包装现有 `ReadOnlyToolExecutor`，增加安全层：
- Registry 验证：只执行 category=read_only 的已注册工具
- PathGuard 扩展：额外阻断 `.claude/` 目录
- Secret detection：阻断 .env/证书/密钥/token/私钥
- Output redaction：脱敏处理
- Audit trail：每次执行记录到审计摘要

### 支持的操作
- `read_file`: 读取项目文件（PathGuard + .claude 阻断 + secret 阻断）
- `list_dir`: 列出目录
- `git_status`: git status 只读
- `git_log`: git log 只读
- `git_diff_summary`: git diff --stat 只读
- `query_docs`: 列出 docs 目录
- `query_tests`: 列出测试文件

### API
- `POST /tools/readonly/run`: 执行只读工具操作
  - 入参: {tool_id, operation, params}
  - 出参: {status, output, audit_record}

## 安全边界
- 项目目录内
- 不读 .env、证书、密钥、token、私钥
- 不读 .claude/
- 不路径穿越
- 不允许 shell 任意命令
- 输出脱敏

## 文件
- NEW: `readonly_tool_runner.py` (~160 lines)
- NEW: `readonly_tool_runner_api.py` (~45 lines)
- NEW: `tests/test_readonly_tool_runner.py` (~120 lines)
- MODIFY: `app.py`
