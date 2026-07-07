# M58 决策：Local Release Checklist

## 决策
新增 LocalReleaseChecklistService，作为 M57 ReleaseReadiness 的增强版，以结构化清单形式呈现发布前置检查。

## 关键设计选择

### 1. 复用 M57 而非重构
M58 的检查项（审计完整性、证据安全、代码状态等）与 M57 的 ReleaseReadiness 有重叠。选择保留两套独立服务：
- M57：快速 ready/not-ready 判定
- M58：详细 checklist 含分类和建议

两者共享底层只读 git 查询和 secret scan 逻辑。

### 2. 发布确认项
新增 `release_confirm` 检查项，固定返回 pass，强调"本工具为只读，不执行发布"。

### 3. 类型拆分
将 ReleaseReadiness 和 LocalReleaseChecklist 类型从 protocol-autonomy.ts 拆到 protocol-release.ts，控制单文件在 300 行以内。

### 4. 不下沉到 Electron 主进程
保持 API 通信模式，不在 Electron 主进程直接调用 git，确保只读边界清晰。

## 不做的
- 不提供"一键发布"按钮
- 不自动执行 git tag / push / release
- 不修改文件系统
- 不绕过 PermissionGate
