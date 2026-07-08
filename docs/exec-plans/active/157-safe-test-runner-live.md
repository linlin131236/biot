# M157 Exec Plan — Safe Test Runner Live：安全测试运行器真实接入

> 当前基线：M156 已完成并 push（a413720），后端 `TestRunnerIntegration` 已有白名单测试命令和 7 个后端测试，但前端缺少 UI 组件。
> 本 milestone 补齐前端测试运行器面板和 API 集成。

---

## 参考资料

本次开工前实际读取 2 篇 BinCloud 资料：

1. `E:\BinCloud\知识库\03-知识\AI工程\Agent安全加固指南.md`
   - 采用原则：工具调用日志必须脱敏；敏感信息自动过滤；最小权限原则。
   - 落点：测试输出必须脱敏后才进入前端 UI。

2. `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md`
   - 采用原则：用户第一屏应该是可用工作台，所有状态必须能解释下一步，中文 UI。
   - 落点：测试运行器显示运行前确认、运行中状态、通过/失败结果、脱敏输出。

---

## 现状分析

### 已有（M109 基础设施）
- 后端：`test_runner_integration.py` — `TestRunnerIntegration` 支持白名单测试命令、危险参数过滤、输出脱敏、结构化结果
- 后端：`test_runner_integration_api.py` — `/tools/test-runner/run`、`/tools/test-runner/available`、`/tools/test-runner/history` 端点
- 后端：`app.py` 已注册 router
- 后端测试：`test_test_runner_integration.py`（7 个测试）
- 前端：`harnessClientAutonomy.ts` 缺少 test runner API 函数
- 前端：`PanelsSection.tsx` 缺少 TestRunnerPanel 装配

### 缺口
| 缺口 | 严重性 | 说明 |
|------|--------|------|
| 前端无测试运行器 UI | P1 | 用户无法在桌面端选择和运行白名单测试 |
| 前端无 API 函数 | P1 | `harnessClientAutonomy.ts` 缺少 `fetchTestRunnerAvailable`、`runTest`、`fetchTestRunnerHistory` |
| 前端无测试 | P2 | 无前端测试覆盖测试运行器场景 |

---

## 执行方案

### 改动 1：前端 API 函数（P1）

**文件**：`apps/desktop/src/harnessClientAutonomy.ts`

**操作**：
新增 3 个函数：`fetchTestRunnerAvailable`、`runTest`、`fetchTestRunnerHistory`

### 改动 2：TestRunnerPanel 组件（P1）

**文件**：`apps/desktop/src/TestRunnerPanel.tsx`（新建）

**功能**：
- 加载可用测试列表（白名单）
- 下拉选择测试
- 确认运行对话框（显示测试描述和超时时间）
- 运行中状态
- 结果展示（通过/失败/超时/阻止，颜色区分）
- 脱敏输出展示（`<pre>` 块）
- 运行历史列表

### 改动 3：面板装配（P1）

**文件**：`apps/desktop/src/PanelsSection.tsx`

**操作**：
添加 `TestRunnerPanel` 到面板列表，传入 API 函数

### 改动 4：前端测试（P2）

**文件**：`apps/desktop/src/TestRunnerPanel.test.tsx`（新建）

**新增测试**：
1. 加载状态
2. 测试选项加载
3. 确认对话框
4. 运行结果展示
5. 错误状态
6. 白名单提示
7. 脱敏输出
8. 无危险操作按钮

---

## 验收标准

1. ✅ 只允许白名单测试命令
2. ✅ 运行前显示命令、工作目录、预计影响，需要用户确认
3. ✅ 不允许任意 shell
4. ✅ 输出脱敏
5. ✅ UI 显示运行中、成功、失败、取消
6. ✅ targeted tests 覆盖白名单、非白名单拒绝、输出脱敏、状态切换
7. ✅ 所有 UI 文案中文
8. ✅ `pnpm run quality` 通过
9. ✅ `git diff --check` 通过
10. ✅ renderer 无危险暴露
11. ✅ 无 `as any` / `unknown as`
12. ✅ 无私人称呼

---

## 实施顺序

1. 前端 API 函数（`harnessClientAutonomy.ts`）
2. TestRunnerPanel 组件（`TestRunnerPanel.tsx`）
3. 面板装配（`PanelsSection.tsx`）
4. 前端测试（`TestRunnerPanel.test.tsx`）
5. 运行 targeted tests
6. 运行 full quality gates
7. 写 decision + review gate + project-state 更新
8. commit

---

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 测试运行器 UI 过于复杂 | 低 | 保持简约风格，与现有面板一致 |
| 后端白名单列表变化 | 低 | 前端从 `/tools/test-runner/available` 动态加载，不硬编码 |
| 输出脱敏由后端负责 | 低 | `TestRunnerIntegration._redact()` 已实现，前端只展示后端返回的数据 |

---

## 不改动的部分

- `test_runner_integration.py` — 后端引擎已完整，不动
- `test_runner_integration_api.py` — API 路由已完整，不动
