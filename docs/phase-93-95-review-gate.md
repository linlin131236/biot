# M93-M95 Review Gate — 审计时间线 + 诊断中心 + 发布准备页

## 状态：✅ 通过

## 必查项
- [x] M93 审计时间线可读、可追溯、按时间排序
- [x] M93 每个节点中文状态、来源、证据引用
- [x] M93 无执行按钮
- [x] M94 诊断中心统一展示阻断/警告/提示
- [x] M94 每条诊断有中文原因、影响、建议
- [x] M94 区分"必须修复"和"可接受风险"
- [x] M94 不自动修复
- [x] M95 发布准备页 ready/not ready 状态
- [x] M95 检查项、阻断项、警告、建议动作
- [x] M95 明确只读、无 release/tag/push/delete
- [x] 所有面板中文 UI
- [x] 无 `as any` / `unknown as`
- [x] renderer 无危险 API
- [x] 所有文件 ≤300 行

## 测试结果
| 面板 | 测试数 | 结果 |
|------|--------|------|
| AuditTimelinePanel | 6 | ✅ |
| DiagnosticsCenterPanel | 6 | ✅ |
| ReleaseReadinessPanel | 7 | ✅ |
| Desktop full (30 files) | 250 | ✅ |
| Build | - | ✅ |

## 新增文件
- `audit_timeline_api.py` (38行)
- `diagnostics_center_api.py` (35行)
- `AuditTimelinePanel.tsx` (131行) + test (69行)
- `DiagnosticsCenterPanel.tsx` (139行) + test (53行)
- `ReleaseReadinessPanel.tsx` (132行) + test (66行)
