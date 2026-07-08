# M158 Exec Plan — Task Result Summary

> 当前基线：M157 已完成并 push（e0c57fc）。AgentLoop 只返回最后一步，TaskClosure 有丰富生命周期但无结构化结果摘要。本 milestone 补齐结构化结果摘要能力。

## 现状分析

### 已有
- `AgentLoopResult`（status, steps, last_step, error）
- `TaskClosureService` 记录 commands, command_results, changed_files, events, review_summary
- `task_closure_api.py` 提供 CRUD 端点
- `GoalConsole.tsx` 展示状态、步数、时间线
- 无 `TaskResultSummary` 类型

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 无结构化结果摘要 | P1 | 前端无法获取 { status, steps, duration, changed_files, commands, final_output, error, review_summary } |
| 无摘要 endpoint | P1 | 没有 GET /task-closures/{id}/result-summary |
| 无摘要类型 | P1 | packages/shared/src 无 TaskResultSummary 接口 |

## 执行方案

### 改动 1：后端 result_summary 方法
**文件**：`services/agent-core/src/bolt_core/task_closure_service.py`

新增 `result_summary(closure_id)` 方法，从 closure 数据合成结构化摘要：
```python
def result_summary(self, closure_id: str) -> dict:
    closure = self._record(closure_id).closure
    events = self._record(closure_id).events
    # 计算 duration（created_at 到最后一个事件的时间）
    # 统计 changed_files 数量
    # 提取最后 5 个 command_results
    # 返回结构化 dict
```

### 改动 2：后端 endpoint
**文件**：`services/agent-core/src/bolt_core/task_closure_api.py`

新增 `GET /task-closures/{closure_id}/result-summary` 端点，调用 `service.result_summary()`。

### 改动 3：共享类型
**文件**：`packages/shared/src/protocol-autonomy.ts`

新增 `TaskResultSummary` 接口：
```typescript
export interface TaskResultSummary {
  closure_id: string;
  status: string;
  steps: number;
  duration_seconds: number;
  changed_files: string[];
  commands: string[];
  command_results: string[];
  final_output: string | null;
  error: string | null;
  review_summary: string | null;
  next_action: string | null;
  retry_count: number;
  permission_requests: string[];
}
```

### 改动 4：前端 API 函数
**文件**：`apps/desktop/src/harnessClientAutonomy.ts`

新增 `fetchTaskResultSummary(baseUrl, closureId)` 函数。

### 改动 5：前端展示
**文件**：`apps/desktop/src/GoalConsole.tsx`

在 GoalConsole 中添加 `TaskResultSummary` 展示区域：
- 状态 + 步数 + 耗时
- 变更文件列表
- 命令执行结果（脱敏展示）
- 错误信息
- 审查摘要 + 下一步建议

### 改动 6：测试
- 后端：`test_task_closure_service.py` 新增 `test_result_summary_completed`, `test_result_summary_failed`, `test_result_summary_empty`
- 前端：`GoalConsole.test.tsx` 新增结果摘要展示测试

## 验收标准
1. ✅ `GET /task-closures/{id}/result-summary` 返回结构化摘要
2. ✅ 摘要包含 status, steps, duration, changed_files, commands, final_output, error, review_summary
3. ✅ 前端 GoalConsole 展示结构化结果摘要
4. ✅ 所有 UI 文案中文
5. ✅ `pnpm run quality` 通过
6. ✅ `git diff --check` 通过
7. ✅ 无 `as any` / `unknown as`
8. ✅ renderer 无危险暴露

## 实施顺序
1. 共享类型 (protocol-autonomy.ts)
2. 后端 result_summary 方法
3. 后端 endpoint
4. 后端测试
5. 前端 API 函数
6. 前端展示
7. 前端测试
8. 运行 tests + quality gates
9. 写 decision + review gate + project-state
10. commit
