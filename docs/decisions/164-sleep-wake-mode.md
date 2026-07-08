# M164 Decision — Sleep/Wake Mode

> 基线：M163 已完成并 push（5cbc41b）。没有空闲/待机模式。本 milestone 添加 Sleep/Wake 模式。

## 决策

**通过**。M164 已补齐 Sleep/Wake 模式。P2 缺口已修复。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `services/agent-core/src/bolt_core/sleep_wake_engine.py` | 新建 SleepWakeEngine | P2 后端 |
| `services/agent-core/src/bolt_core/sleep_wake_api.py` | 新建 sleep/wake/status 端点 | P2 后端 |
| `services/agent-core/src/bolt_core/app.py` | 注册 sleep-wake router | 集成 |
| `apps/desktop/src/SleepWakePanel.tsx` | 新建待机控制面板 | P2 前端 |
| `apps/desktop/src/SleepWakePanel.test.tsx` | 新建 6 个前端测试 | P2 测试 |

## 验证

- Backend: 6 passed
- Frontend: 6 passed
- Desktop: 50 files / 367 tests
- quality: PASS
