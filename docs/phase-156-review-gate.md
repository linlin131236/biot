# M156 Phase Review Gate — Approval Apply Desktop Flow

> 基线：M155 已 push（836683b）。

## Gate 检查清单

### 1. 实现完成

| 检查项 | 状态 | 证据 |
|--------|------|------|
| 前端 apply API 函数 | PASS | `harnessClientAutonomy.ts` 新增 `applyApproval` 函数 |
| 前端 apply 测试 | PASS | `harnessClientAutonomy.test.ts`：3 个新测试 |
| 后端集成测试补充 | PASS | `test_approval_apply_api.py`：2 个新测试（API 注入 approval、过期提案） |

### 2. Targeted Tests

| 套件 | 结果 | 数量 |
|------|------|------|
| `test_approval_apply.py` | PASS | 19/19 |
| `test_approval_apply_api.py` | PASS | 4/4 |
| `harnessClientAutonomy.test.ts` | PASS | 22/22 |

### 3. Full Quality

| 检查项 | 结果 |
|--------|------|
| `pnpm run quality` | PASS |
| `git diff --check` | PASS |
| `check-docs.mjs` | PASS |
| `check-chinese-ui.mjs` | PASS |

### 4. 安全扫描

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `as any` / `unknown as` | PASS | 未命中 |
| renderer 暴露 | PASS | 未命中 |
| PermissionGate bypass | PASS | 未命中 |
| auto-approve | PASS | 未命中 |
| 密钥/token 泄露 | PASS | 未命中 |

### 5. Chinese UI

| 检查项 | 结果 |
|--------|------|
| 所有 UI 文案中文 | PASS | apply 结果中的错误信息均为中文 |
| 无私人称呼 | PASS | 未出现"爸爸"/"爸" |
| 无 mojibake | PASS | `check-chinese-ui.mjs` 通过 |

### 6. Git 状态

仅 `.claude/` 和 exec plan 未跟踪，无其他未提交改动。

## Reviewer 结论

**M156 PASS**。所有 Gate 检查通过，无 P0/P1/P2 问题。

## 变更文件

- `apps/desktop/src/harnessClientAutonomy.ts`
- `apps/desktop/src/harnessClientAutonomy.test.ts`
- `services/agent-core/tests/test_approval_apply_api.py`
- `docs/decisions/156-approval-apply-desktop-flow.md`
- `docs/phase-156-review-gate.md`（本文件）
