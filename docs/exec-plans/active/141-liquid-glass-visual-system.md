# M141 Liquid Glass Visual System

## 目标

把桌面端从功能堆叠推进到可公开展示的中文产品界面：

- 主工作台采用液态玻璃视觉系统。
- 深色和浅色主题都可用。
- 软件内不出现私人称呼，统一使用“用户、人工批准、用户确认”等产品化文案。
- 写入、apply、恢复、发布等安全边界继续保留，不新增自动批准或自动执行入口。

## 范围

- `LiquidGlassWorkbench` 桌面壳层。
- `LiquidGlassHome` 首页任务输入体验。
- `LiquidGlassSettings` 设置中心基础结构。
- 液态玻璃 CSS tokens、流光边框、浅色主题 tokens。
- 可能被桌面 UI 展示的后端中文返回文案。

## 非目标

- 不接入新的模型供应商。
- 不实现真实自动执行。
- 不修改 PermissionGate 安全语义。
- 不 push、release、tag、delete。

## 实施步骤

1. 新增视觉 token 测试，先让缺失 token 和流光边框测试失败。
2. 重写液态玻璃工作台、首页和设置页中文文案。
3. 增加深色/浅色 theme token，加入慢速 `biotBorderFlow` 边框动效。
4. 清理软件内私人称呼，统一为产品化称谓。
5. 用浏览器实机验证深色、浅色、中文文案、玻璃模糊和流光边框。
6. 跑 targeted tests、desktop build、quality、backend full tests。
7. 补 review gate 与 project-state 后提交。

## 验收标准

- `apps/desktop/src` 不出现私人称呼。
- 产品相关后端返回文案不出现私人称呼。
- `LiquidGlassDesignTokens.test.ts` 验证 token 与 `biotBorderFlow`。
- 浏览器实机检查深色和浅色主题都通过。
- `pnpm run quality` 通过。
- `uv run pytest -q` 通过。
