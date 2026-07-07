# M120 Exec Plan - Agent Intelligence Dogfood

目标：完成 V7 智能评估阶段的大复盘，不新增执行能力，只做只读门禁检查。

范围：
- 汇总 M111-M119 的 9 个 eval/dogfood 模块和测试文件是否齐全。
- 复查 M101-M110 工具生态核心文件仍存在。
- 检查 V7 新增代码没有自动 push/release/tag/delete。
- 检查 approval apply 和 permission contract 仍作为写入门控。
- 检查 V7 文档链完整：M111-M120 exec plan、decision、review gate。
- 检查 project-state 更新到 M120、未 push、未进入 M121。

验收：
- M120 dogfood 返回 18 项检查。
- 任一缺失项必须进入 p1_failures。
- API 只读返回检查结果，不执行修复、写入、发布或推送。
