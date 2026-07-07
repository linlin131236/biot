# M112 Decision — 补丁应用评估

## 决策
建立 PatchApplyEvalService，在临时目录中使用 ApprovalApplyEngine 对固定案例集进行补丁应用安全评估。

## 设计选择
1. **临时目录运行**：不修改真实项目文件，每个 case 独立子目录
2. **12 个 eval cases**：3 成功（单文件/新建/多文件），9 失败（diff不匹配、注入、路径阻断×2、过期、agent自批、scope不匹配、无批准、绕过）
3. **复用 WriteProposalStore + ApprovalApplyEngine**：不重新实现 apply 逻辑
4. **_approve / _stale helper**：直接操作 store._proposals 设置状态以模拟审批流程
5. **API 只读**：GET /tools/eval/patch-apply/run 在 TemporaryDirectory 中运行

## 风险
- 低风险：在临时目录运行，不碰真实文件
- 架构豁免：check-architecture.mjs 已添加豁免（临时目录写入）
