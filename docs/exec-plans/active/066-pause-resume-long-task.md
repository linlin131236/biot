# M66 执行计划：Pause/Resume Long Task

## 目标
建立长任务暂停/恢复能力，暂停后禁止副作用，恢复时重新验证权限。

## 参考资料
- M62 Execution State Machine：paused 状态和转换规则
- M61 Task Graph：节点状态对接

## 实现方案

### 后端
- `bolt_core/pause_resume.py`：PauseResumeService
  - pause(): 快照当前状态，限制只能从 running/ready 暂停
  - resume(): 3 项检查（快照完整性、权限重验证、状态转换）、返回行动方案
  - cancel_pause(): 取消暂停 → failed
  - is_paused / get_paused_nodes / get_snapshot
- `bolt_core/pause_resume_api.py`：
  - POST /pause-resume/pause
  - POST /pause-resume/resume
  - POST /pause-resume/cancel
  - GET /pause-resume/status/{id}
  - GET /pause-resume/paused

## 验收标准
- [x] 暂停捕获快照（状态、时间、原因、证据引用）
- [x] 恢复时 3 项安全检查
- [x] 恢复后需重新通过 PermissionGate
- [x] 不能从 completed/failed/pending 暂停
- [x] 不能重复暂停
- [x] 22 个 targeted tests
