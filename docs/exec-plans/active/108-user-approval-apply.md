# M108 Exec Plan — User Approval Apply 批准后应用补丁
## 目标：建立"批准后才写入"的 apply 闭环
## 设计：ApprovalApplyEngine — 10 道安全检查 + 真文件写入 + 审计
## 验收：13 tests pass，真实文件变更验证
