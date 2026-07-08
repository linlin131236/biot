# M164 Exec Plan — Sleep/Wake Mode

> 当前基线：M163 已完成并 push（5cbc41b）。没有空闲/待机模式，GoalRunner 只在显式启动时运行。本 milestone 添加 Sleep/Wake 模式。

## 执行方案

### 改动 1：SleepWakeEngine
**文件**：`services/agent-core/src/bolt_core/sleep_wake_engine.py`（新建）

```python
class SleepWakeEngine:
    def sleep(self, duration_seconds: int) -> dict
    def wake(self, trigger: str) -> dict
    def get_status(self) -> dict
```

### 改动 2：后端 endpoint
**文件**：`services/agent-core/src/bolt_core/sleep_wake_api.py`（新建）

- `POST /sleep-wake/sleep` - 进入待机
- `POST /sleep-wake/wake` - 唤醒
- `GET /sleep-wake/status` - 当前状态

### 改动 3：前端
- `SleepWakePanel.tsx` - 待机/唤醒面板
- 后端测试 + 前端测试

## 验收
1. ✅ Sleep/Wake 状态机
2. ✅ 中文 UI
3. ✅ quality gates
