# Decision 142: Liquid Glass Component System

## 决策

新增轻量的 Liquid Glass primitives，用组件约束按钮、面板、pill 和 toolbar 的视觉与交互合同。

## 原因

M141 已经证明视觉方向可行，但样式仍分散在页面级 CSS 中。继续直接堆页面会导致后续面板质感不一致，也会让 hover、disabled、玻璃边框、浅色主题适配重复出现。

## 方案

- `GlassButton`：统一按钮尺寸、variant、icon、disabled。
- `GlassPanel`：统一玻璃面板、标题、说明、流光边框。
- `GlassPill`：统一状态胶囊与强调色。
- `GlassToolbar`：统一工具条布局。

## 安全边界

- primitives 只渲染 UI，不接触文件系统、shell、ipcRenderer 或 process。
- 不新增任何执行、批准或发布入口。
- 所有用户可见文案保持中文。
