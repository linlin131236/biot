# M120 Review Gate - Agent Intelligence Dogfood

结论：V7 智能评估阶段以 M120 为终点，完成后停止，等待爸爸复审。

门禁：
- Tool Call Eval：通过
- Patch Apply Eval：通过
- Test Failure Diagnosis Eval：通过
- Permission Boundary Eval：通过
- Multi-Agent Collaboration Eval：通过
- Memory Retrieval Eval：通过
- Chinese Interaction Eval：通过
- E2E Task Dogfood：通过
- Failure Recovery Dogfood：通过
- M101-M110 工具生态安全文件仍存在
- 无自动 push/release/tag/delete
- 不绕过 PermissionGate
- 不自动 approve
- renderer 无危险暴露
- 无 `as any` / `unknown as`
- M111-M120 文档链完整
- project-state 更新到 M120
- 未进入 M121

放行条件：以上 18 项全部通过，且 full tests / quality 通过。
