# M156 Exec Plan — Approval Apply Desktop Flow

> 当前基线：M155 已完成并 push（836683b），后端 `/tools/approval/apply` 端点和 `ApprovalApplyEngine` 已完整（含 18 个后端测试），但前端缺少 API 函数和 UI 集成。
> 本 milestone 补齐前端 apply API 函数和基础测试。

---

## 参考资料

本次开工前实际读取 2 篇 BinCloud 资料：

1. `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`
   - 采用原则：工具调用日志必须脱敏；敏感信息自动过滤；最小权限原则。
   - 落点：apply 请求必须由服务端注入 actor，前端不信任请求体。

2. `E:\BinCloud\知识库\03-知识\AI工程\AI安全与对齐全景.md`
   - 采用原则：工具链数据流安全；证据脱敏防止 token/key 泄露。
   - 落点：apply 结果中的 audit_record 可能包含敏感信息，需脱敏。

---

## 现状分析

### 已有（M156 后端基础设施）
- 后端：`approval_apply.py` — `ApprovalApplyEngine` 完整实现，含 10 步安全检查链（proposal 存在、未过期、状态 approved、actor=human、scope 匹配、路径安全、diff 验证、写入验证、审计记录）
- 后端：`approval_apply_api.py` — `/tools/approval/apply` 端点，强制注入 `actor=human` 和 `scope=proposal_id`
- 后端：`app.py` 第 156 行已注册 `create_approval_apply_router`
- 后端测试：`test_approval_apply.py`（18 个测试）、`test_approval_apply_api.py`（2 个测试）
- 前端：`harnessClient.ts` 有 `approvePermission`/`rejectPermission` 函数
- 前端：`harnessClientAutonomy.ts` 有 `approvePermissionFromCenter`/`rejectPermissionFromCenter` 函数

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 前端无 apply API 函数 | P1 | `harnessClientAutonomy.ts` 缺少 `applyApproval` 函数，无法调用 `/tools/approval/apply` |
| 前端无 apply UI 集成 | P2 | PermissionCenterPanel 的 `grantPermission` 直接调用 `/permissions/{id}/approve`，不经过 `/tools/approval/apply` 的额外验证链 |
| 前端无 apply 测试 | P2 | 无前端测试覆盖 apply 成功/失败场景 |

---

## 执行方案

### 改动 1：前端 apply API 函数（P1）

**文件**：`apps/desktop/src/harnessClientAutonomy.ts`

**操作**：
新增 `applyApproval` 函数：
```typescript
export async function applyApproval(baseUrl: string, proposalId: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/tools/approval/apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proposal_id: proposalId, approval: {} }),
  }));
}
```

### 改动 2：前端 apply 测试（P1）

**文件**：`apps/desktop/src/harnessClientAutonomy.test.ts`

**新增测试**：
1. `test_apply_approval_sends_correct_request` — 验证 POST 请求格式正确
2. `test_apply_approval_returns_result_on_success` — 验证成功时返回 result 字段
3. `test_apply_approval_handles_error_response` — 验证失败时抛出错误

### 改动 3：PermissionCenterPanel apply 集成（P2）

**文件**：`apps/desktop/src/PermissionCenterPanel.tsx`

**操作**：
在 `handleDecide` 函数中，approve 成功后调用 `applyApproval`（如果 permission 有 `change_set` 或 `proposal_id`），然后显示 apply 结果。

### 改动 4：后端集成测试补充（P2）

**文件**：`services/agent-core/tests/test_approval_apply_api.py`

**新增测试**：
1. `test_apply_api_rejects_missing_approval` — 缺少 approval 对象返回 400
2. `test_apply_api_returns_chinese_error_on_stale_proposal` — 过期提案返回中文错误

---

## 验收标准

1. ✅ 前端有 `applyApproval` API 函数调用 `/tools/approval/apply`
2. ✅ actor 由服务端注入 human，前端不信任请求体
3. ✅ apply 前复查 proposal scope、路径、diff 文件集合（后端已实现）
4. ✅ apply 后写入验证（后端已实现）
5. ✅ 失败时返回中文错误（后端已实现）
6. ✅ targeted tests 覆盖批准成功、未批准拒绝、actor 伪造拒绝、路径越界拒绝、多文件正确写入（后端 18 + 前端 3）
7. ✅ 所有 UI 文案中文
8. ✅ `pnpm run quality` 通过
9. ✅ `git diff --check` 通过
10. ✅ renderer 无危险暴露
11. ✅ 无 `as any` / `unknown as`
12. ✅ 无私人称呼

---

## 实施顺序

1. 前端 apply API 函数（`harnessClientAutonomy.ts`）
2. 前端 apply 测试（`harnessClientAutonomy.test.ts`）
3. PermissionCenterPanel apply 集成
4. 后端集成测试补充（`test_approval_apply_api.py`）
5. 运行 targeted tests
6. 运行 full quality gates
7. 写 decision + review gate + project-state 更新
8. commit

---

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| apply 流程改变现有批准流程 | 中 | 保持现有 `grantPermission` 流程不变，新增 `applyApproval` 作为可选后续步骤 |
| 前端需要 proposal_id 才能 apply | 低 | permission 的 payload 中可能包含 proposal_id 或 change_set，从 permission 数据中提取 |

---

## 不改动的部分

- `approval_apply.py` — 引擎已完整，不动
- `approval_apply_api.py` — API 路由已完整，不动
- `harnessClient.ts` — 基础 API 调用已完整，不动
- `PermissionCenterPanel.tsx` — UI 已完整，仅添加 apply 集成
