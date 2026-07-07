# M91 Decision — 中文任务首页

## 决策
新增只读聚合端点 `GET /task-home` 和对应的中文桌面面板 `TaskHomePanel`，作为 V5 产品化第一屏。

## 选型

### 后端聚合方式
- **方案 A**：前端直接调多个 API 聚合 → 选型为后端聚合
- **选择**：后端单端点聚合 (`GET /task-home`)
- **理由**：
  1. 减少前端往返次数，首页加载只需 1 次请求
  2. 聚合逻辑在后端，桌面渲染逻辑保持简单
  3. 复用现有服务引用，不新增 Harness 依赖
  4. 单端点更易于测试和监控

### 信息层级
- **阻断 → 警告 → 提示 → 下一步建议**
- 阻断项红色标识，权限待批高亮，当前目标独立展示区域
- 遵循参考资料的产品原则：第一屏是工作台，不是说明页

### 边界
- 纯只读：无 POST/PUT/DELETE 操作
- 无 approve / push / release / delete / execute 按钮或入口
- 不暴露 ipcRenderer / fs / shell / process
- 所有文案中文

## 实现内容
- `task_home.py` (161 行)：TaskHomeSummary 数据类 + TaskHomeService 聚合服务
- `task_home_api.py` (30 行)：单端点 `GET /task-home`，返回中文摘要
- `TaskHomePanel.tsx` (154 行)：中文任务首页面板
- `TaskHomePanel.test.tsx` (97 行)：10 个测试（正常/空/错误/中文/无危险按钮）
- `test_task_home.py` (171 行)：13 个单元测试
- `test_task_home_api.py` (68 行)：10 个 API 测试（受 pydantic 环境问题影响暂不能运行）
- `protocol-autonomy.ts`：新增 TaskHomeSummary / TaskHomeEvent 类型
- `harnessClientAutonomy.ts`：新增 fetchTaskHome()
- `PanelsSection.tsx`：TaskHomePanel 放在最前面作为第一屏
- `app.py`：注册 task_home_router

## 测试结果
- 后端单元测试：13/13 passed
- 前端面板测试：10/10 passed（含在 222 total desktop tests）
- Shared 测试：27/27 passed
- Desktop build：passed
- Quality：passed
- `as any`/`unknown as`：CLEAN
- Renderer 暴露：CLEAN
