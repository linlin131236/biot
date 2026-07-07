# Phase 100 Review Gate - 桌面 Beta Dogfood 大复盘

## 状态
复审修复后通过，等待爸爸最终复审。

## M100 必查项
| # | 检查 | 结果 |
|---|------|------|
| 1 | M91 任务首页文件、路由、文档链完整 | 通过 |
| 2 | M92 权限中心文件、路由、文档链完整 | 通过 |
| 3 | M93 审计时间线文件、路由、文档链完整 | 通过 |
| 4 | M94 诊断中心文件、路由、文档链完整 | 通过 |
| 5 | M95 发布准备页文件、路由、文档链完整 | 通过 |
| 6 | M96 多任务队列文件、路由、文档链完整 | 通过 |
| 7 | M97 失败解释文件、路由、文档链完整 | 通过 |
| 8 | M98 会话恢复文件、路由、文档链完整 | 通过 |
| 9 | M99 设置/模型/工具文件、路由、文档链完整 | 通过 |
| 10 | 所有 M91-M99 面板包含中文文案 | 通过 |
| 11 | renderer 无危险 API 和类型逃逸 | 通过 |
| 12 | 无自动批准、自动执行、push/release/tag/delete 入口 | 通过 |
| 13 | M100 后停止，未进入 M101 | 通过 |

## 修复说明
- `DesktopBetaDogfoodService` 不再硬编码 13/13 通过，而是读取项目目录做真实检查。
- 任一关键文件、路由、独立 exec plan、decision、phase review gate 缺失，都会导致 `ready_for_next=false`。
- 新增反向测试：空项目目录必须让 dogfood gate 失败。

## 验证记录
- `uv run pytest -q services/agent-core/tests/test_desktop_beta_dogfood.py`：5 passed。
- `pnpm --filter @bolt/desktop test -- SettingsToolsPanel.test.tsx`：实际运行 desktop 全套，34 files / 262 tests passed。
- `pnpm --filter @bolt/desktop test`：34 files / 262 tests passed。
- `pnpm --filter @bolt/desktop build`：通过。
- `pnpm --filter @bolt/shared test`：27 passed。
- `pnpm run quality`：通过。
- `uv run pytest -q --color=no`（在 `services/agent-core`）：1225 passed, 1 warning。
- 当前全量测试基线：1225 backend + 27 shared + 262 desktop = 1514 passed。
- `git diff --check`：通过，仅 Windows LF/CRLF 提示。
- `node scripts/check-docs.mjs`：通过。
- `node scripts/check-chinese-ui.mjs`：通过。

## 结论
V5 中文产品 UI/UX 的桌面可见性目标达成：爸爸可以从桌面看到任务、权限、审计、诊断、发布准备、多任务、失败解释、会话恢复和设置策略。M100 完成后停止，未进入 M101。
