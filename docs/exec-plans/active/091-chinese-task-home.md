# M91 Exec Plan — 中文任务首页

## 目标
把桌面第一屏做成中文任务工作台，爸爸打开就能看到：当前目标、运行状态、权限待处理数、审计风险、诊断阻断、下一步建议。

## 参考资料
1. `E:\BinCloud\知识库\03-知识\方法论\Agent产品化流水线.md`
   - 采用原则：PRD 必须有"一句话产品定位 + 核心功能清单 + 验收标准"
   - 采用原则：第一屏必须是可用工作台，不是说明页
2. `E:\BinCloud\知识库\03-知识\方法论\20260628_讨论场到执行系统_ZCode看板法.md`
   - 采用原则：每条状态必须可客观验证、不给选择题只给填空题
   - 采用原则：owner/deadline/验收标准三要素
3. `E:\BinCloud\知识库\03-知识\AI工程\OpenClaw实际场景学习报告.md`
   - 采用原则：优先级排序（阻断→警告→提示三层信息层级）
   - 采用原则：失败必须有中文原因和建议动作
4. `D:\Bolt\Bolt\docs\桌面AI编程Agent全流程架构对比.md`
   - 采用原则：第7层产品体验——工作区选择、模型配置、权限面板、轨迹可视化

## 技术方案

### 后端：只读聚合服务
新增 `task_home.py` + `task_home_api.py`：
- 单端点 `GET /task-home` 返回聚合 summary
- 聚合来源：goals（未完成数/状态）、permissions（pending 数）、diagnostics（阻断/警告数）、execution audit timeline（最近事件）、planner graphs（活跃任务图）
- 纯只读，不创建/修改/批准/删除任何东西
- 不新增 Harness 依赖，复用已有 services

### 前端：TaskHomePanel
新增 `apps/desktop/src/TaskHomePanel.tsx`：
- 展示区域：当前目标 → 运行状态 → 权限待处理 → 审计/诊断风险 → 下一步建议
- 紧凑但有层次的信息布局
- 无 push/release/delete/approve 按钮
- 不暴露 ipcRenderer/fs/shell/process

### 接入
- `PanelsSection.tsx`：加入 TaskHomePanel，放在最前面作为第一屏
- `harnessClientAutonomy.ts`：新增 `fetchTaskHome()` 函数
- `protocol-autonomy.ts`：新增 `TaskHomeSummary` 类型

## 验收标准
- [ ] 首页展示：当前目标、运行状态、权限待处理数量、诊断阻断/警告数、下一步建议
- [ ] 无 push/release/delete/approve 按钮
- [ ] renderer 无危险 API
- [ ] 中文 UI 全部
- [ ] 测试覆盖：正常数据、空数据、API 错误、中文文案
- [ ] 所有测试通过（targeted + full）
- [ ] quality 检查通过
- [ ] 文件均 ≤300 行

## 风险
- 低：纯只读聚合，不写任何状态，不引入新依赖
