# Phase 38 Review Gate

## M38 实现摘要
（待补）

## 改动文件
（待补）

## 不自动恢复说明
桌面重启后发现未完成长任务，默认不自动继续执行。用户必须点击"恢复任务"。

## pending_permission 行为
显示"已暂停"+"等待人工批准"，不自动批准。

## max_steps 行为
显示"已停止"+"已达到最大步数"。

## failed 行为
显示"失败"+ 错误信息 + 下一步建议。

## 安全边界
- 不新增危险工具能力
- 不绕过 permission gate
- renderer 不出现 ipcRenderer/fs/shell/process

## 测试结果
（待补）

## Reviewer 明天重点
（待补）
