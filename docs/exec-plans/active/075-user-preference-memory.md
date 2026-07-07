# M75 User Preference Memory — 执行计划

## 目标
建立爸爸偏好记忆，严格受控。只记录明确表达过的长期偏好，不从一次性上下文乱推断。

## 参考资料
- `E:\BinCloud\知识库\03-知识\AI工程\20260628_上下文工程_Context_Engineering.md` — 记忆分层
- `docs/桌面AI编程Agent全流程架构对比.md` — Biot产品定位

## 数据源
- `docs/project-state.md`：硬规则（权威来源）
- 固定内置偏好：全中文、称呼爸爸、不自动push/release/tag/delete

## 实现文件
| 文件 | 用途 |
|------|------|
| `services/agent-core/src/bolt_core/user_preference_memory.py` | UserPreferenceMemoryService + PreferenceRecord |
| `services/agent-core/src/bolt_core/user_preference_memory_api.py` | API router |
| `services/agent-core/tests/test_user_preference_memory.py` | tests |
| `services/agent-core/tests/test_user_preference_memory_api.py` | API tests |
| `services/agent-core/src/bolt_core/app.py` | 注册 router |
