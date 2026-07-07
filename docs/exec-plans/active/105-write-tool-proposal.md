# M105 Exec Plan — Write Tool Proposal 写入工具提案

## 目标
写入类工具不能直接写文件，只能生成结构化 proposal。

## 设计

### WriteProposal (frozen dataclass)
- `proposal_id`: uuid
- `tool_id`: 关联的工具 ID
- `target_files`: 目标文件列表
- `operation_type`: create | modify | delete
- `before_summary`: 修改前摘要
- `after_summary`: 修改后摘要
- `diff_preview`: unified diff 预览（不落地）
- `risk_level`: low | medium | high | critical
- `required_permissions`: 所需权限列表
- `rollback_hint`: 回滚提示
- `chinese_explanation`: 中文说明
- `git_head`: 绑定 git HEAD
- `status`: pending | approved | applied | cancelled | expired | stale
- `created_at`: 时间戳

### WriteProposalStore
- `create(proposal)`: 创建提案
- `get(proposal_id)`: 查询
- `list(status=None)`: 列出
- `cancel(proposal_id)`: 取消
- `check_stale(proposal_id)`: 检查 HEAD 是否变化

### 安全规则
- target_file 超出项目目录 → 失败
- secret/cert 文件目标 → 失败
- 不直接写文件，不落地 patch

## 文件
- NEW: `write_tool_proposal.py` (~140 lines)
- NEW: `write_tool_proposal_api.py` (~40 lines)
- NEW: `tests/test_write_tool_proposal.py` (~90 lines)
- MODIFY: `app.py`
