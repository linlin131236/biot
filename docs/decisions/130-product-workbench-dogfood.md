# M130 Decision - Product Workbench Dogfood

## 决策

用独立 dogfood gate 收束 M126-M129，而不是把检查混进已有 beta readiness。

## 理由

- M126-M129 是 M125 之后的产品化补强，不应污染此前 M100/M110/M120/M125 的历史门禁。
- 独立 gate 能清楚回答：工作台是否可见、中文、只读、安全、文档完整。

## 安全边界

- dogfood 只读扫描文件和快照。
- 不执行 apply。
- 不运行测试命令。
- 不 push / release / tag / delete。

