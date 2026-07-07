# M57 Decision: Release Readiness Review Gate

## 决策
新增 ReleaseReadinessService，汇总 integrity、diagnostics、evidence redaction、git status 等多个检查源，返回统一的 readiness 结果。API 端点 GET /release-readiness。

## 设计
- ReleaseReadinessService 依赖：audit_store、diagnostics_service、integrity_service、project dir path
- 方法 `assess() -> dict` 返回：
  - ready: bool
  - checks: list[dict] 每个包含 code / label / passed / severity / detail
  - blockers: list[str]
  - warnings: list[str]
- 不调用 shell、不修改文件、不自动执行

## 检查逻辑
| 检查项 | 通过条件 | 失败 severity |
|---|---|---|
| integrity | list_integrity 无 blocking | blocking |
| diagnostics | list_diagnostics 无 blocking | blocking |
| timeline evidence | 最近 closure 有 timeline 事件 | warning |
| secret redaction | audit JSON 中无明文敏感值（regex 扫描） | blocking |
| git clean | git status --porcelain 源码改动为空 | blocking |
| branch sync | git rev-parse HEAD == origin/main | warning |
| docs consistency | project-state.md 提及最新 phase | warning |
| review gate exists | phase-{n}-review-gate.md 存在 | warning |

## 排除
- 不自动执行 git push / release / tag / delete
- 不做网络调用
- 不创建/modify 文件
