# M79 Memory Search UI — 执行计划

## 目标
给桌面端增加只读记忆搜索入口，让爸爸能查决策、失败、偏好、项目画像、代码地图。UI 必须中文、只读、安全。

## 参考资料
- 现有 `CheckpointPanel.tsx` — 面板组件模式参考
- 现有 `harnessClientAutonomy.ts` — API client 模式参考
- `docs/桌面AI编程Agent全流程架构对比.md` — 第7层产品体验

## 实现文件
| 文件 | 用途 |
|------|------|
| `apps/desktop/src/MemorySearchPanel.tsx` | 搜索面板组件 |
| `apps/desktop/src/MemorySearchPanel.test.tsx` | 组件测试 |
| `apps/desktop/src/PanelsSection.tsx` | 集成到面板区 |
| `apps/desktop/src/harnessClientAutonomy.ts` | 新增 5 个 API client 方法 |
| `packages/shared/src/protocol-autonomy.ts` | 新增 MemorySearchResult 类型 |

## 验收标准
- [x] 搜索关键词能查到 decision/failure/preference/code map
- [x] 空结果中文提示
- [x] 敏感记忆显示脱敏/阻断提示
- [x] 前端 tests 覆盖渲染、搜索、filter、无危险对象
- [x] `pnpm --filter @bolt/desktop test` 通过
- [x] `pnpm --filter @bolt/desktop build` 通过
