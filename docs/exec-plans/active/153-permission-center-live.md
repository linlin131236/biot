# M153 Exec Plan — Permission Center Live：权限中心真实接入

> 当前基线：M152 已完成并 push，权限中心面板已有真实后端接入（M92 基础设施），但 payload_summary 未脱敏，可能暴露敏感 token/path 细节。
> 本 milestone 不新增功能，只做安全和真实性的补全加固。

---

## 参考资料

本次开工前实际读取 4 篇 BinCloud/Hermes/Agent 资料：

1. `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`
   - 采用原则：工具调用日志必须脱敏；敏感信息自动过滤；最小权限原则。
   - 落点：`payload_summary` 在展示前必须经过脱敏处理。

2. `E:\BinCloud\知识库\03-知识\AI工程\AI安全与对齐全景.md`
   - 采用原则：工具链数据流安全；证据脱敏防止 token/key 泄露。
   - 落点：后端在返回权限数据时即完成脱敏，前端不做安全假设。

3. `E:\BinCloud\知识库\03-知识\学习\AI工程课程\AI工程-Phase18-伦理安全对齐-深度笔记.md`
   - 采用原则：工具输出是不可信输入，不能直接变成 UI 展示内容；必须经过清洗/脱敏。
   - 落点：payload 数据来自 agent 工具请求，不可信，必须脱敏后才进入前端。

4. `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md`
   - 采用原则：用户第一屏应该是可用工作台，所有状态必须能解释下一步，中文 UI。
   - 落点：权限中心空状态和错误状态已有中文，保持不动。

---

## 现状分析

### 已有（M92 基础设施）
- 后端：`permission_center_api.py` + `permission_center.py` — `/permission-center` 端点已接入真实 `PermissionQueue`，返回中文风险分类、影响说明。
- 前端：`PermissionCenterPanel.tsx` — 已接入真实 API（`fetchPermissionCenter`、`approvePermission`、`rejectPermission`），有批准/拒绝按钮、风险标签、空状态。
- 测试：`test_permission_center.py`（7 个后端测试）、`test_permission_center_api.py`（1 个集成测试）、`PermissionCenterPanel.test.tsx`（9 个前端测试）。
- 流程：approve/reject 通过 `/permissions/{request_id}/approve` 和 `/permissions/{request_id}/reject` 走 PermissionGate，成功后刷新列表。

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| `payload_summary` 未脱敏 | P1 | `permission_center.py` 第 166 行 `str(p.payload)[:200]` 直接暴露原始 payload，可能包含 API key、token、文件路径等敏感信息 |
| 无脱敏测试 | P2 | 后端和前端测试均未覆盖 payload 脱敏场景 |

---

## 执行方案

### 改动 1：后端 payload 脱敏（P1）

**文件**：`services/agent-core/src/bolt_core/permission_center.py`

**操作**：
1. 在文件顶部导入 `redact` 函数：`from bolt_core.evidence_redactor import redact`
2. 在第 166 行，将 `payload_str = str(p.payload)[:200]` 改为：
   ```python
   payload_str = redact(str(p.payload))[:200] if p.payload else "无附加数据"
   ```
3. 脱敏优先（`redact()` 先替换敏感模式），然后截断到 200 字符，避免 UI 溢出。

**为什么在这里脱敏**：
- 后端脱敏是唯一安全边界。前端只展示后端返回的数据，不应对原始 payload 做任何安全假设。
- `evidence_redactor.py` 已有成熟的红名单模式（API_KEY、TOKEN、SECRET、PASSWORD、Bearer、sk-xxx、私钥、证书），直接复用。
- 前端不需要改任何代码——脱敏后的数据流入前端，前端只负责展示。

### 改动 2：后端脱敏测试（P2）

**文件**：`services/agent-core/tests/test_permission_center.py`

**新增测试**：
1. `test_payload_redacted_for_api_key` — payload 包含 `API_KEY=xxx` 时，`payload_summary` 不包含原始 key。
2. `test_payload_redacted_for_token` — payload 包含 `TOKEN=xxx` 时，`payload_summary` 包含 `[已脱敏]`。
3. `test_payload_redacted_for_bearer` — payload 包含 `Bearer xxx` 时，脱敏为 `Bearer [已脱敏]`。

### 改动 3：前端脱敏展示测试（P2）

**文件**：`apps/desktop/src/PermissionCenterPanel.test.tsx`

**新增测试**：
1. `test_payload_summary_does_not_expose_api_key` — 当 backend 返回含 API key 的 payload_summary 时，UI 不显示原始 key。

---

## 验收标准

1. ✅ 有 pending 时真实显示（已有，不动）。
2. ✅ 无 pending 时中文空状态（已有，不动）。
3. ✅ approve/reject 后刷新（已有，不动）。
4. ✅ 无自动批准（已有，不动）。
5. ✅ payload_summary 中不出现原始 API key / token / secret / Bearer token。
6. ✅ 脱敏后仍保留操作意图（如 `{"cmd":"npm test"}` 不变，`{"api_key":"sk-xxx"}` 变为 `{"api_key":"[已脱敏]"}`）。
7. ✅ 测试覆盖脱敏场景。
8. ✅ `pnpm run quality` 通过。
9. ✅ `git diff --check` 通过。
10. ✅ renderer 无危险暴露（PermissionCenterPanel 不改动，天然安全）。
11. ✅ 无 `as any` / `unknown as`。
12. ✅ 无私人称呼。

---

## 实施顺序

1. 写后端脱敏代码（`permission_center.py`）
2. 写后端脱敏测试（`test_permission_center.py`）
3. 写前端脱敏展示测试（`PermissionCenterPanel.test.tsx`）
4. 运行 targeted tests
5. 运行 full quality gates
6. 写 decision + review gate + project-state 更新
7. commit
8. 停止，等待审核

---

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 脱敏后 payload_summary 可能变得不可读 | 低 | `redact()` 只替换已知敏感模式，保留操作意图。`str(p.payload)` 中的命令、文件路径等非敏感内容保持不变。 |
| `evidence_redactor` 依赖路径可能变化 | 极低 | `from bolt_core.evidence_redactor import redact` 是标准相对导入，与 `permission_center.py` 同目录。 |
| 前端测试 mock 数据需包含脱敏后格式 | 低 | 新增测试用含敏感信息的 mock 数据，验证 UI 不显示原始值。 |

---

## 不改动的部分

- `PermissionCenterPanel.tsx` — UI 已完整，无需改动。
- `harnessClient.ts` — API 调用已完整，无需改动。
- `PanelsSection.tsx` — 面板装配已完整，无需改动。
- `permission_center_api.py` — API 路由已完整，无需改动。
- `permission_queue.py` — 队列逻辑已完整，无需改动。
- `app.py` — 路由注册已完整，无需改动。
