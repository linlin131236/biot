# Bolt Project State

## 当前稳定基线

- 已完成到：M128 Test Feedback Lane（本地完成，待后续 M129-M130 继续）。
- 最新远端基线：`origin/main = 6d128b0 docs: mark audit hardening pushed`。
- 当前本地分支：`main` 基于 `origin/main` 开始 M126。
- 未 push / 未 release / 未 tag / 未 delete。
- 未进入 M129。

## 当前状态

- M55-M125 已完成并 push。
- 外部审计硬化已完成并 push。
- M126 新增只读 Agent 工作台：
  - 后端：`product_workbench.py`、`product_workbench_api.py`。
  - 前端：`ProductWorkbenchPanel.tsx`，已接入桌面第一屏。
  - API：`GET /product-workbench`。
- M127 新增补丁批准检查清单：
  - 字段：`patch_approval`。
  - 检查：补丁预览、目标范围锁定、人工批准、过期复查、审计记录。
  - UI：只读展示“补丁批准检查”，无批准按钮。
- M128 新增白名单测试回填：
  - 字段：`test_feedback`。
  - 测试项：后端单元、后端 API、共享模块、桌面测试、桌面构建、全量质量门。
  - UI：只读展示“白名单测试回填”，无任意命令输入框。
- 工作区：存在 M126 本地改动；`.claude/` 未跟踪、未提交，按规则保持。

## M126 验证

- `uv run pytest -q services/agent-core/tests/test_product_workbench.py`：6 passed。
- `pnpm --filter @bolt/desktop test -- ProductWorkbenchPanel.test.tsx`：36 files / 275 tests passed。

## M126 参考资料

- `Agent产品化流水线.md`：串行契约优先，需求、计划、实现、验证、复盘要形成稳定流水线。
- `20260628_讨论场到执行系统_ZCode看板法.md`：任务要有状态、验收标准和下一步。
- `OpenClaw实际场景学习报告.md`：项目状态、心跳、检查清单和恢复路径要可见。

## 已知风险

- `harnessClientAutonomy.ts` 超过 300 行，属于历史豁免文件，后续可专项拆分。
- M61 Task Graph / M81-M89 多 Agent 工作流仍以纯内存为主，后续可评估持久化。
- M126-M128 工作台当前是只读聚合层，不替代真实批准、apply、测试和恢复执行链路。
- `.claude/` 未跟踪、未提交，按规则保持。

## 下一步建议

- 继续 M129 Failure And Recovery Lane，把失败解释和恢复前检查展示得更清楚。
- M130 做 Product Workbench Dogfood 后停止，等待爸爸复审。

## 长期硬规则

- 所有用户可见 UI 必须中文。
- 不自动 push、release、tag、delete。
- 不进入未授权 milestone。
- 不绕过 PermissionGate。
- 不自动执行危险命令。
- 不自动批准权限。
- 不提交生成物、缓存、虚拟环境、证书材料、`.bolt`、`uv.lock`。
- 不使用 `as any` / `unknown as`。
- renderer 不暴露 `ipcRenderer` / `fs` / `shell` / `process`。
- 每个 milestone 必须产出 exec plan + decision + phase review gate + project-state 更新 + commit。
