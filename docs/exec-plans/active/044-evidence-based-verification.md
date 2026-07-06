# M44 Evidence-Based Verification

## 目标
让任务闭环从记录 Agent Loop 过程升级为基于证据评估完成度，并给出下一步修复建议。

## 范围
- 后端新增 Verification Plan 和 Verification Assessment。
- TaskClosureService 可生成验证计划、只读评估、手动更新评估结果。
- API 暴露 verification-plan 与 assessment 端点。
- shared protocol 与桌面 client 对齐新结构。
- TaskClosurePanel 展示验证计划、验收状态、缺少证据、建议修复。
- App 级狗粮覆盖创建闭环、绑定运行、评估完成度。

## 不做
- 不自动执行验证命令。
- 不自动批准 permission。
- 不自动 push / release / delete。
- 不绕过 PermissionGate。
- 不把 Agent Loop executed 直接当完成。
- 不进入 M45。

## 验证计划与命令建议
Verification Plan 描述应该验证什么，以及现有 evidence 是否满足。`command` 字段只是命令建议，用于提示用户可手动运行什么；M44 不执行该命令，也不把它渲染为执行按钮。

## 完成判断
完成必须来自保守证据组合：变更文件或相关工具证据，加测试、文档检查、质量门或审查通过证据。单纯 `tool:*`、读取文件、普通输出、Agent Loop completed 只能说明执行过，不能单独说明任务完成。

## 阻止状态
- `waiting_permission`：停在等待人工批准。
- `stopped`：停在最大步数，需要重新规划或人工处理。
- `failed`：进入修复建议，不转 completed。
- 缺少验证证据：保持未完成，提示缺少项。

## UI
桌面端显示中文验收状态：验证计划、验收状态、已通过、未通过、缺少证据、建议修复、等待人工批准、评估完成度、不执行命令、命令建议、已满足、未满足。

## 验证
- 后端 verification/service/API：59 passed。
- 后端 integration smoke：3 passed。
- shared vitest：23 passed。
- desktop client/panel/dogfood 最小验证：通过。
