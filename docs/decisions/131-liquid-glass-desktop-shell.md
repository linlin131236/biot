# M131 Decision - Liquid Glass Desktop Shell

## 决策

采用“液态玻璃中文 Agent 工作台”作为 Biot 桌面端主视觉：首页保持极简任务输入，设置中心采用左侧分类导航，工程面板折叠保留。

## 理由

- 爸爸确认的设计方向是高级、科技、液态玻璃，而不是传统后台仪表盘。
- Agent 桌面产品第一屏应该优先回答“今天让 Biot 做什么”，不是把所有工程面板堆满屏幕。
- 设置中心需要接近成熟桌面 Agent 产品：分类清楚、密度适中、中文完整、权限边界显眼。
- 旧工程面板仍有调试和验证价值，M131 先折叠保留，后续再逐步产品化。

## 安全边界

- 本次只改桌面 UI 壳层和样式。
- 不新增后端执行能力。
- 不新增自动 approve / apply / retry / resume。
- 不新增 push / release / tag / delete 入口。
- renderer 仍不直接访问 ipcRenderer / fs / shell / process。
