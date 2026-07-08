# M135 Checkpoint Restore Semantics 执行计划

## 背景

M132-M134 已经让本地 API、真实模型默认配置和工具结果回填更接近真实 Agent 闭环。当前 checkpoint 仍只支持创建和读取快照，不能把快照内容明确恢复到工作区文件，因此“恢复”语义不完整。

## 目标

1. 为 `CheckpointService` 增加真实 restore 语义。
2. 恢复必须由调用方显式确认，不能自动触发。
3. 只恢复 checkpoint 中记录的工作区内文件。
4. `.env`、密钥、credentials 等秘密路径不入库、不写回。
5. 增加 API 路由，未确认时返回中文 400。

## 非目标

- 不做 `git reset`、`git checkout` 或任何仓库级回滚。
- 不自动批准恢复操作。
- 不接入 UI 批准按钮。
- 不恢复大文件、二进制文件或证书材料。

## 实施步骤

1. 先补服务层和 API 层失败测试。
2. 实现 `CheckpointService.restore()`。
3. 创建 checkpoint 时跳过秘密路径内容。
4. 增加 `POST /checkpoints/{checkpoint_id}/restore`。
5. 跑 targeted tests、full tests、quality、文档和安全扫描。
6. 更新 review gate 与 project-state，并提交 M135。

## 验收标准

- 显式确认后，checkpoint 中保存的普通文件内容能恢复。
- 未确认时不写文件，并返回 `confirmation_required` 或 HTTP 400。
- 秘密路径不进入 checkpoint 内容，也不会在 restore 时写回。
- 恢复目标不能越过 workspace 边界。
- 无自动 push、release、tag、delete、approve。
