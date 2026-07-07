# M121 Review Gate - Crash Recovery

结论：M121 只读崩溃恢复准备度门禁完成后，才允许进入 M122。

门禁：
- 检查点服务存在。
- 暂停/恢复服务存在。
- 会话恢复入口存在。
- 审计完整性检查存在。
- 线程接手摘要存在。
- 长任务恢复复盘存在。
- M121 exec plan、decision、review gate 完整。
- project-state 标记 M121，且未进入 M122。

禁止项：
- 不自动恢复。
- 不自动批准权限。
- 不自动 push/release/tag/delete。
