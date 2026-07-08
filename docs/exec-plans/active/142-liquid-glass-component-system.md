# M142 Liquid Glass Component System

## 目标

把 M141 的液态玻璃视觉沉淀成可复用组件系统，降低后续权限中心、补丁预览、审计页和设置页继续打磨时的重复样式。

## 范围

- 新增 `LiquidGlassPrimitives.tsx`。
- 新增 primitives 测试。
- 增补共享 CSS class：按钮、面板、pill、toolbar。
- 首页和设置页逐步接入 primitives。

## 非目标

- 不重写所有历史面板。
- 不新增自动执行能力。
- 不修改 PermissionGate。
- 不 push、release、tag、delete。

## 验收标准

- primitives 有独立测试覆盖。
- 首页原有动作按钮仍可触发。
- 设置页分类仍可访问。
- 产品源码不出现私人称呼。
- `pnpm run quality` 通过。
