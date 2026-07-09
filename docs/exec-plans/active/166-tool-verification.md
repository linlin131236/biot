# M166 Tool Verification 执行计划

## 目标

提供只读工具链健康验证，让 Loop 在继续前能看到关键工具是否可用。

## 验收标准

- `/tools/verify` 返回工具清单、状态、总数和健康数。
- 验证过程只读，不执行写入、push、release、tag、delete。
- 桌面面板中文展示验证结果。
- targeted tests、quality、Chinese UI、diff check 通过。

## 风险

- 工具验证不能变成自动执行工具。
- claim 必须由 API 返回值和测试佐证。
