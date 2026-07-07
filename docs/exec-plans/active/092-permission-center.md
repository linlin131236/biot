# M92 Exec Plan — 权限中心

## 目标
把权限状态集中成中文权限中心：哪些权限在等爸爸、风险是什么、为什么需要、批准后会发生什么。

## 参考资料
1. ZCode看板法 — owner/deadline/验收标准三要素，不给选择题只给填空题
2. Agent产品化流水线 — PRD 必须有验收标准
3. OpenClaw场景报告 — 优先级排序（高→低风险），失败必须中文原因
4. 桌面AI编程Agent全流程架构对比 — Claude Code的per-tool+per-scope权限模型

## 技术方案

### 后端：权限聚合服务
新增 `permission_center.py` + `permission_center_api.py`：
- 单端点 `GET /permission-center` 返回聚合权限列表
- 每条权限附加：风险等级（high/medium/low）、风险中文说明、批准后会发生什么、工具中文名、操作中文名
- 风险分类逻辑：写操作/执行操作→高风险，读操作→中风险，查询→低风险
- 纯只读，不新增 approve/reject 端点
- 复用现有 PermissionQueue

### 前端：PermissionCenterPanel
- 展示：权限列表、风险等级标识、工具/操作中文说明、原因、批准后影响
- 筛选：按风险等级/工具/状态筛选
- 高风险权限醒目标注（红色边框）
- 现有 approve/reject 按钮只能走 PermissionGate 路径
- 不新增 approve 入口

### 共享类型
- `PermissionCenterItem` 接口

## 验收
- [ ] 中文解释权限来源、风险等级、请求工具、操作内容、建议动作
- [ ] 高风险权限醒目标注
- [ ] 无绕过 PermissionGate 的路径
- [ ] 测试覆盖 pending/approved/rejected/denied/empty/error 状态
- [ ] 所有文件 ≤300 行
