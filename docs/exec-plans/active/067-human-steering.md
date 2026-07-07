# M67 Human Steering — 执行计划

## 目标
允许用户在长任务运行中安全转向、补充、暂停、要求复查。Steering 只改变计划/状态/上下文，不绕过 PermissionGate，不直接执行危险动作。

## 参考资料
| # | 文件 | 采用原则 |
|---|------|---------|
| 1 | `AI工程-Phase14-Agent工程-深度笔记-上.md` | Lesson 01：Agent Loop 五大必需品（停止条件、轮次预算）；Lesson 02：ReWOO 规划-执行分离，Planner 可被 steering 重新触发 |
| 2 | `AI工程-Phase14-Agent工程-深度笔记-下.md` | Lesson 26：Agent 失败模式（范围蔓延、上下文丢失、工具误用）→ steering 作为人的纠正手段；Lesson 27：PVE 模式——人在回路确认 |
| 3 | `20260628_AgentHarness20层进化指南.md` | s03 权限三道闸门：白名单→规则→用户确认；s04 Hooks 挂在循环上不侵入；s05 任务计划可被 steering 改写 |
| 4 | `桌面AI编程Agent全流程架构对比.md` | 关键数据流：`Tool Request → Permission Check → Execute → Trace Record → Tool Result → Next Context`；Biot 定位：Claude 安全粒度 + Codex 流畅执行 |

## 范围
- 新增 `HumanSteeringService`：分类用户输入 → 生成安全 steering 结果
- 新增 API router：`POST /runs/{run_id}/steering` 增强版
- 集成 M66 PauseResumeService（pause steering 走 M66 规则）
- 所有结果记录到 conversation store + trace log
- **不执行 shell、不写文件、不调用 approve_permission**

## 架构设计

### 分类体系
| Intent | 触发关键词 | 安全级别 | 行为 |
|--------|-----------|---------|------|
| `continue` | 继续/go on/resume/proceed | 低 | 记录意图，返回确认 |
| `pause` | 暂停/pause/stop/wait | 中 | 通过 M66 PauseResumeService 暂停 |
| `change_goal` | 改成/改为/修改目标/change goal | 高 | 只记录 pending 建议，不直接修改目标 |
| `request_review` | 检查/复查/review/看看/审视 | 低 | 记录审查请求 |
| `abort` | 取消/终止/放弃/abort/cancel | 高 | 只记录 pending 建议，不直接终止进程 |
| `unknown` | 无法识别 | 低 | 返回中文降级说明，建议明确指令 |

### 数据流
```
用户输入 → classify() → 分类结果
  ├─ continue → 记录 evidence → 返回中文确认
  ├─ pause → M66 PauseResumeService.pause() → 记录 evidence → 返回结果
  ├─ change_goal → 记录 pending 建议 → 返回"需人工确认"
  ├─ request_review → 记录 evidence → 返回中文确认
  ├─ abort → 记录 pending 建议 → 返回"需人工确认"
  └─ unknown → 返回中文降级说明
```

### 安全边界
- 不调用 `harness.approve_permission`
- 不调用 `harness.submit_tool_request`
- 不执行 shell
- 不写文件
- change_goal/abort 只生成 pending 状态，不直接执行
- pause 走 M66 完整安全检查链

## 产出文件
- `services/agent-core/src/bolt_core/human_steering.py`
- `services/agent-core/src/bolt_core/human_steering_api.py`
- `services/agent-core/tests/test_human_steering.py`
- `services/agent-core/tests/test_human_steering_api.py`
- 修改 `services/agent-core/src/bolt_core/app.py`：替换旧 steering 端点
- `docs/exec-plans/active/067-human-steering.md`（本文件）
- `docs/decisions/067-human-steering.md`
- `docs/phase-67-review-gate.md`

## 验收标准
- [x] 6 种 intent 全部分类正确
- [x] continue steering 可记录
- [x] pause steering 不绕过 M66 规则
- [x] change_goal/abort 只生成 pending，不直接执行
- [x] unknown steering 有中文降级说明
- [x] 所有结果含中文解释
- [x] 所有结果含 requires_human_confirmation 字段
- [x] 所有结果可进入 conversation/trace 证据链
- [x] 不调用 approve_permission
- [x] 不执行 shell
- [x] 不写文件
- [x] targeted tests 覆盖所有分支
- [x] 全量测试通过
