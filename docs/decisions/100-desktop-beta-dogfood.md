# M100 Decision - 桌面 Beta Dogfood

## 决策
M100 作为 V5 大复盘 gate，必须做可验证检查：文件存在、路由注册、逐 M 文档链、中文 UI、安全边界和未进入 M101。

## 原因
大复盘不能只写“通过”。如果 gate 不检查真实证据，就不能作为进入 M101 的依据。

## 结果
- `DesktopBetaDogfoodService` 改为读取项目目录进行真实检查。
- 任一关键文件、文档或路由缺失都会导致 `ready_for_next=false`。
- 保持只读，不执行测试命令、不 push、不 release。
