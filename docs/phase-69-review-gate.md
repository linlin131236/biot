# Phase 69 Review Gate — Long Task Recovery Dogfood

## 状态：✅ 通过

## 范围
- 新增 `LongTaskRecoveryDogfoodService`：9 项只读 readiness 检查
- 检查项覆盖 M61-M68 关键路径：task graph、state machine、pause/resume permissions、steering safety、budget blocking、failure classifier Chinese、retry loop safety、PermissionGate integrity、traceability
- 新增 API：`GET /dogfood/long-task-recovery`
- **不新增自动执行器**

## 测试
- targeted tests：20 passed
- 全量 backend pytest：804 passed（无回退）
- shared tests：27 passed
- desktop tests：195 passed
- desktop build：通过

## 安全边界
- [x] 不新增 shell 自动入口
- [x] 不新增 push/release/tag/delete 自动入口
- [x] 不新增 approve 自动入口
- [x] 不绕过 PermissionGate
- [x] dogfood service 只读，无 execute/run/apply 方法
- [x] 中文 UI 检查通过
- [x] 无 `as any` / `unknown as`

## dogfood 检查结果
全部 9 项检查均可执行，所有服务级检查通过：
1. ✅ 任务图（M61）
2. ✅ 状态机（M62）
3. ✅ 暂停恢复权限复查（M66）
4. ✅ 人工转向安全（M67）
5. ✅ 预算阻断（M68）
6. ✅ 失败分类中文诊断（M64）
7. ✅ 安全重试循环（M65）
8. ✅ PermissionGate 安全底座
9. ✅ 证据追溯

## 是否允许进入下一 milestone
**✅ 允许进入 M70 Agent Workflow Beta（大复盘门）。**
