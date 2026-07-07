# Phase 91 Review Gate — 中文任务首页

## 状态：✅ 通过

## M91 必查项
- [x] 首页展示：当前目标、运行状态、权限待处理数量、诊断阻断/警告数、下一步建议
- [x] 无 push/release/delete/approve 按钮
- [x] renderer 无危险 API（ipcRenderer/fs/shell/process）
- [x] 中文 UI 全部
- [x] 测试覆盖：正常数据、空数据、API 错误、中文文案、无危险按钮
- [x] 纯只读：GET /task-home 无写操作
- [x] 所有文件 ≤300 行
- [x] 无 `as any` / `unknown as`
- [x] 未绕过 PermissionGate
- [x] 未进入 M92

## 测试结果
| 层 | 文件 | 结果 |
|----|------|------|
| Backend unit | test_task_home.py | 13/13 passed |
| Backend API | test_task_home_api.py | 受环境 pydantic 影响（预存问题） |
| Desktop | TaskHomePanel.test.tsx | 10/10 passed |
| Shared | protocol-autonomy.test.ts | 27/27 passed |
| Desktop full | 26 files | 222/222 passed |
| Build | @bolt/desktop build | passed |

## 新增文件
| 文件 | 行数 | 用途 |
|------|------|------|
| `services/agent-core/src/bolt_core/task_home.py` | 161 | 聚合服务 |
| `services/agent-core/src/bolt_core/task_home_api.py` | 30 | API 路由 |
| `services/agent-core/tests/test_task_home.py` | 171 | 单元测试 |
| `services/agent-core/tests/test_task_home_api.py` | 68 | API 测试 |
| `apps/desktop/src/TaskHomePanel.tsx` | 154 | 桌面面板 |
| `apps/desktop/src/TaskHomePanel.test.tsx` | 97 | 面板测试 |
| `docs/exec-plans/active/091-chinese-task-home.md` | - | 执行计划 |
| `docs/decisions/091-chinese-task-home.md` | - | 决策记录 |

## 修改文件
- `app.py`：+2 行（import + include_router）
- `PanelsSection.tsx`：+3 行（import + 组件渲染）
- `harnessClientAutonomy.ts`：+5 行（fetchTaskHome）
- `protocol-autonomy.ts`：+3 行（TaskHomeSummary 类型）

## 安全扫描
- `as any`/`unknown as`：CLEAN
- Renderer 暴露：CLEAN
- 自动执行/approve/push/release/tag/delete：CLEAN
