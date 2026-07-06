# M40 Decision: Safe Checkpoints

## 决策
Checkpoint 是审计/恢复前置，不是自动回滚。

## 要点
- 创建和加载检查点
- 加载只展示摘要，不写文件
- 没有 restore API 前，不做自动回滚
- 后端已有 _CP_ID_PATTERN 路径校验
- 恶意 id 由后端拒绝，前端只传 URL segment
- UI 中文
