# Phase 57 Review Gate

## 状态：已完成/已验证（含 P1/P2 修复）

## 覆盖范围
- 新增 ReleaseReadinessService：汇总 integrity / secret scan / git clean / branch sync / docs consistency / review gate 检查
- 新增 GET /release-readiness API 端点
- 前端新增发布准备度面板（中文）
- P1 修复：_scan_secrets 排除已脱敏占位符（[已脱敏]），同时兼容 JSON escaped Unicode 形式
- P2 修复：动态解析 project-state.md 当前 milestone；扫描最高编号 phase-*-review-gate.md；去硬编码 M57
- 测试：12 个 release readiness 测试（含脱敏占位符不阻断、明文+脱敏混合检测）

## 安全硬线
- 未自动批准 PermissionGate。
- 未绕过 PermissionGate。
- 未自动执行 git push/release/tag/delete。
- 未新增自动执行入口。
- git 操作仅为只读查询。
- API 返回结果不包含可执行命令。
- renderer 未新增危险暴露。
- 未使用 `as any` / `unknown as`。

## 已跑验证
- `uv run pytest tests/test_release_readiness.py tests/test_release_readiness_api.py -q`：10 passed。
- `uv run pytest -q`：539 passed。
- `pnpm --filter @bolt/shared test`：27 passed。
- `pnpm --filter @bolt/desktop test`：195 passed。

## 自审
- 已检查：ReleaseReadinessService 只读，不修改文件、不执行命令。
- 已检查：git 操作带超时和错误捕获（timeout=10, OSError）。
- 已检查：secret scan 复用 evidence_redactor 的 _PATTERNS。
- 已检查：前端 Readiness 组件处理 null 数据（显示"加载中..."）。
- 已检查：所有检查项 label 为中文。

## 是否 push
- 未 push。
