# M57 Execution Plan: Release Readiness Review Gate

## 目标
把 M55 integrity、M56 redaction、M51 timeline、M53 diagnostics 汇总成一个只读"发布前准备度"检查。不 release、不 tag、不 push，只告诉人：现在能不能考虑发布，以及阻断项是什么。

## 范围
- 只读 API + 中文 UI
- 不自动修复、不自动执行命令、不自动 approve
- 不替代人工 review，只作为 release 前 checklist

## 检查项
1. execution audit integrity clean
2. execution diagnostics clean
3. 最近 closure 有 timeline evidence
4. audit/closure evidence 未发现 secret 明文
5. 当前工作区无 staged/unstaged 源码改动
6. 当前 branch 与 origin 是否同步（只读展示）
7. docs/project-state.md 与 phase gate 一致
8. phase-xx-review-gate.md 存在
9. 不出现 release/tag/delete 自动按钮

## 实现步骤
1. 写 exec plan 和 decision
2. 新增 release_readiness.py 和 release_readiness_api.py
3. 修改 app.py 接 router
4. 更新前端类型和 fetch
5. UI 展示（复用现有面板或新增）
6. 写测试
7. 更新 docs

## 涉及文件
- 新增：services/agent-core/src/bolt_core/release_readiness.py
- 新增：services/agent-core/src/bolt_core/release_readiness_api.py
- 修改：services/agent-core/src/bolt_core/app.py
- 修改：packages/shared/src/protocol-autonomy.ts
- 修改：apps/desktop/src/harnessClientAutonomy.ts
- 修改：apps/desktop/src/ExecutionHandoffPanel.tsx
- 新增：services/agent-core/tests/test_release_readiness.py
- 新增：services/agent-core/tests/test_release_readiness_api.py
