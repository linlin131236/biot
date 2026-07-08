# M160 Exec Plan — Builder Execution Engine

> 当前基线：M159 已完成并 push（7dc2bef）。Builder 只有协议契约（BuilderOutput dataclass），没有执行引擎。本 milestone 升级为能实际产生代码变更的执行引擎。

## 现状分析

### 已有
- `BuilderOutput` dataclass（code_changes, tests, evidence_refs, source_refs）
- `FileWriter`（propose_file_write + apply_file_write）
- `PatchEngine`（build_change_set + apply_change_set + can_apply_change）
- `atomic_write`（atomic_write_text）
- `PathGuard`（workspace boundary check）
- `TestRunnerIntegration`（whitelisted test runner）

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 无 Builder 执行引擎 | P1 | 不能根据任务描述产生代码变更 |
| 无 builder endpoint | P1 | 没有 `POST /builder/execute` |
| 无前端 BuilderPanel | P2 | 桌面端无 Builder 面板 |

## 执行方案

### 改动 1：BuilderEngine
**文件**：`services/agent-core/src/bolt_core/builder_engine.py`（新建）

```python
class BuilderEngine:
    def execute_task(self, task_description: str, workspace: str) -> BuilderOutput:
        # 1. 根据任务描述分析需要变更的文件
        # 2. 使用 FileWriter.propose_file_write() 产生变更提案
        # 3. 运行测试验证
        # 4. 返回 BuilderOutput
```

约束：
- 不直接写文件（只 produce proposals）
- 不自我审批
- 不绕过 PermissionGate
- 通过 PathGuard 检查工作区边界

### 改动 2：后端 endpoint
**文件**：`services/agent-core/src/bolt_core/builder_api.py`（新建）

`POST /builder/execute` - 接收 task_description + workspace，返回 BuilderOutput

### 改动 3：前端
- `harnessClientAutonomy.ts`：新增 `executeBuilderTask`
- `BuilderPanel.tsx`：任务输入、执行按钮、结果展示
- `BuilderPanel.test.tsx`：测试

## 验收标准
1. ✅ BuilderEngine 能根据任务描述产生 BuilderOutput
2. ✅ Builder 不直接写文件（只 produce proposals）
3. ✅ Builder 不自我审批
4. ✅ 所有 UI 文案中文
5. ✅ `pnpm run quality` 通过
6. ✅ `git diff --check` 通过
7. ✅ 无 `as any` / `unknown as`
8. ✅ renderer 无危险暴露
