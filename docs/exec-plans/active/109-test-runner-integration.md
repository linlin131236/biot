# M109 Exec Plan — Test Runner Integration 测试运行接入
## 目标：补丁应用后安全触发测试运行，受权限和预算控制
## 设计：TestRunnerIntegration — 白名单命令 + 超时/大小限制 + 输出脱敏
## 验收：7 tests pass，非白名单命令被阻断
