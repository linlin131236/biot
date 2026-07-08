# M157 Decision — Safe Test Runner Live

> 基线：M156 已完成并 push（a413720），后端 `TestRunnerIntegration` 已有白名单测试命令和 7 个后端测试，但前端缺少 UI 组件。

## 决策

**通过**。M157 的 P1 缺口（前端无测试运行器 UI）已修复。P2 缺口（测试覆盖）已补齐。

## 改动摘要

| 文件 | 改动 | 类型 |
|------|------|------|
| `apps/desktop/src/TestRunnerPanel.tsx` | 新建安全测试运行器面板组件（白名单选择、确认运行、运行中/通过/失败状态、脱敏输出、运行历史） | P1 功能 |
| `apps/desktop/src/TestRunnerPanel.test.tsx` | 新建 8 个前端测试（加载、选项、确认对话框、通过/失败、脱敏输出、无危险按钮） | P1 测试 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 `fetchTestRunnerAvailable`、`runTest`、`fetchTestRunnerHistory` 函数 | P1 功能 |
| `apps/desktop/src/PanelsSection.tsx` | 装配 `TestRunnerPanel` 到面板列表 | P1 集成 |

## 验证结果

- Frontend targeted tests：8 passed（TestRunnerPanel.test.tsx）
- Frontend API tests：22 passed（harnessClientAutonomy.test.ts）
- Backend targeted tests：7 passed（test_test_runner_integration.py）
- Desktop tests：43 files / 325 tests passed（+8 新增测试）
- `pnpm run quality`：通过
- `git diff --check`：通过
- Chinese UI check：通过
- `as any` / `unknown as`：未命中
- renderer 暴露：未命中
- PermissionGate bypass / auto-approve：未命中

## 不做的事

- `test_runner_integration.py` — 后端引擎已完整，不动
- `test_runner_integration_api.py` — API 路由已完整，不动

## 下一步

自动进入 M158 — Task Result Summary。
