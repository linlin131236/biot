# M120 Decision - Agent Intelligence Dogfood

决策：M120 作为 V7 终点，只做只读复盘门禁，不再新增 Agent 执行动作。

采用文件存在性、文档链、状态文档和安全扫描组合检查，确保 M111-M119 的 eval 能被新窗口验证，也确保 M121 未被提前进入。

非目标：
- 不自动修复失败。
- 不自动 approve。
- 不 push、release、tag、delete。
- 不把 eval 结果写入真实项目状态之外的业务文件。

风险处理：
- project-state 不写会因提交而立刻过期的固定远端 hash。
- 若文档链或状态不准确，M120 dogfood 必须失败。
