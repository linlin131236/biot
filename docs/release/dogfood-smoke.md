# Bolt Desktop Dogfood Smoke Test Manual

## 前置条件
1. Agent Core 后端运行：`cd services/agent-core && .venv/Scripts/python -I -m uvicorn bolt_core.app:create_app --factory --host 127.0.0.1 --port 8000`
2. 桌面端启动：`cd apps/desktop && pnpm dev`
3. 准备一个安全临时工作区（如 `D:/tmp/bolt-dogfood`）

## 步骤

### 1. 选择工作区
- 启动桌面端，首次运行向导出现
- 输入工作区路径 `D:/tmp/bolt-dogfood`
- 点击「进入工作台」

### 2. 创建安全小任务
- 在「长任务目标」输入框输入：读取 README.md 内容
- 点击「开始长任务」
- 验证：run ID 出现，状态显示「运行中」

### 3. Agent Loop 运行
- 等待 Agent Loop 执行
- 验证：执行轨迹面板显示事件
- 验证：记忆/感知面板有数据

### 4. 侧聊纠偏
- 在侧聊面板输入修正指令
- 点击「发送指令」或按 Enter
- 验证：steering 注入成功，消息保留在面板
- 禁止：侧聊不能审批 permission 或执行工具

### 5. 人工批准点
- 如果 Agent 请求写文件 → 显示「等待人工批准」
- 点击「批准」或「拒绝」
- 验证：批准后才执行，拒绝后不修改文件
- 禁止：不允许自动审批

### 6. 检查点
- 点击「创建检查点」
- 验证：检查点 ID 显示，包含变更文件数和待审批数
- 输入检查点 ID，点击「加载检查点」
- 验证：只显示摘要，不执行 rollback/write
- 禁止：不允许回滚、写入、删除操作

### 7. 刷新/重启恢复
- 刷新浏览器或重启桌面端
- 验证：显示「发现未完成长任务」banner
- 验证：不自动继续执行
- 点击「恢复任务」后才继续

### 8. 失败路径
- 创建一个会失败的 goal（如 max_steps=1）
- 验证：显示「已停止」「已达到最大步数」
- 不显示「运行中」
- 验证：错误信息中文、短、可操作

### 9. 收集 Evidence/Timeline
- 点击「刷新轨迹」查看 timeline
- 点击「刷新记忆」查看 perception
- 验证：evidence 有具体 action/result

## 明确禁止的行为
- ❌ 自动审批 pending_permission
- ❌ 自动发布代码
- ❌ 自动删除文件
- ❌ 写 workspace 外路径
- ❌ 读取 secrets 文件
- ❌ 侧聊执行工具（只能 steering）
- ❌ 检查点回滚/写入（只能读摘要）
- ❌ 冷启动自动恢复长任务
