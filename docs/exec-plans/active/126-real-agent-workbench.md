# M126 Exec Plan - Real Agent Workbench

## 目标

新增一个只读中文 Agent 工作台，把任务目标、计划、上下文读取、补丁预览、人工批准、apply、测试、审计恢复放在同一条可见流程里。

## 范围

- 后端新增 `product_workbench.py` 和 `product_workbench_api.py`。
- 桌面新增 `ProductWorkbenchPanel.tsx`。
- `PanelsSection` 将工作台放在第一屏。
- 不新增 apply/approve/test/run 按钮，不执行任何危险动作。

## 验收

- `/product-workbench` 返回 8 个中文阶段。
- 安全边界明确：不能自动 apply，不能自动 approve，写入必须爸爸批准。
- 桌面面板中文展示阶段、能力泳道、下一步建议。
- targeted backend 和 desktop tests 通过。

