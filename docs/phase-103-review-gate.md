# M103 Review Gate — Tool Permission Contract 工具权限契约

## 验收清单
| # | 验收项 | 状态 |
|---|--------|------|
| 1 | read-only 工具判定为低风险，无需批准 | ✅ |
| 2 | write/execute/dangerous 工具需要人工批准 | ✅ |
| 3 | push/release/tag/delete 永远标为 dangerous | ✅ |
| 4 | API 层 false/缺失/伪造 approval 都不能变成通过 | ✅ |
| 5 | `approved=true` 无 actor 绕过被拒绝 | ✅ |
| 6 | agent self-approval 被拒绝 | ✅ |
| 7 | scope 不匹配被拒绝 | ✅ |
| 8 | 不自动批准 | ✅ |
| 9 | 不执行工具 | ✅ |

## 测试结果
- **Targeted**: 24/24 passed
- **Backend non-API**: 1041 passed (+24)
- **Security**: 0 `as any` / `unknown as`

## 判定
✅ **M103 通过。进入 M104。**
