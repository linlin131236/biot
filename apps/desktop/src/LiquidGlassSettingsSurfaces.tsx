import { GlassButton, GlassPanel, GlassPill } from './LiquidGlassPrimitives';

type SettingMetric = {
  label: string;
  value: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

type SettingRow = {
  title: string;
  detail: string;
  control: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

type SettingSurface = {
  eyebrow: string;
  title: string;
  summary: string;
  metrics: SettingMetric[];
  rows: SettingRow[];
};

const surfaces: Record<string, SettingSurface> = {
  general: {
    eyebrow: '界面与启动',
    title: '常规设置',
    summary: '控制 Biot 的主题、语言、默认入口和本地安全提示。',
    metrics: [
      { label: '主题', value: '深色液态玻璃', tone: 'success' },
      { label: '语言', value: '简体中文' },
      { label: '启动页', value: 'Agent 工作台' },
    ],
    rows: [
      { title: '界面主题', detail: '深浅色液态玻璃主题保持同一套安全信息层级。', control: '深色液态玻璃', tone: 'success' },
      { title: '界面语言', detail: '所有用户可见文字使用中文，面向公开产品表达。', control: '简体中文' },
      { title: '启动时打开', detail: '启动后默认进入任务驾驶舱，设置中心保留在侧边导航。', control: 'Agent 工作台' },
      { title: '权限模式', detail: '写入、apply、恢复前都需要用户确认。', control: '写入需批准', tone: 'warning' },
    ],
  },
  code: {
    eyebrow: '代码阅读体验',
    title: '代码预览主题',
    summary: '补丁差异、行号和长行折叠都在这里统一管理。',
    metrics: [
      { label: '浅色代码', value: 'GitHub Light' },
      { label: '深色代码', value: 'GitHub Dark', tone: 'success' },
      { label: '行号', value: '显示' },
    ],
    rows: [
      { title: '浅色代码主题', detail: '浅色模式下代码块使用高对比主题，避免玻璃背景影响阅读。', control: 'GitHub Light' },
      { title: '深色代码主题', detail: '深色模式下代码块保持清晰边界和稳定行高。', control: 'GitHub Dark', tone: 'success' },
      { title: '长行自动换行', detail: '补丁和日志过长时自动换行，减少横向滚动。', control: '开启' },
    ],
  },
  model: {
    eyebrow: '模型与密钥边界',
    title: '模型提供方',
    summary: 'API 密钥只显示配置状态，不在界面回显明文。',
    metrics: [
      { label: '连接方式', value: 'OpenAI 兼容' },
      { label: '密钥状态', value: '已配置', tone: 'success' },
      { label: '默认模型', value: '用户选择' },
    ],
    rows: [
      { title: '提供方', detail: '模型供应商和 Base URL 由本地配置管理。', control: 'OpenAI 兼容' },
      { title: 'API 密钥', detail: '只显示是否已配置，保存后立即清空输入框。', control: '仅状态可见', tone: 'warning' },
      { title: '模型选择', detail: '聊天时使用当前选择的模型，不自动切换到未知供应商。', control: '手动选择' },
    ],
  },
  permission: {
    eyebrow: '安全批准链路',
    title: '权限中心',
    summary: '集中查看待批准请求、写入门禁和审计记录，不提供越权入口。',
    metrics: [
      { label: '待批准请求', value: '人工处理', tone: 'warning' },
      { label: '写入门禁', value: '强制开启', tone: 'success' },
      { label: '审计记录', value: '全程保留' },
    ],
    rows: [
      { title: '待批准请求', detail: '工具写入、补丁 apply 和恢复动作进入队列后等待用户确认。', control: '查看队列', tone: 'warning' },
      { title: '写入门禁', detail: '所有写入、apply 和恢复动作都必须等待用户确认。', control: '不可绕过', tone: 'success' },
      { title: '审计记录', detail: '每次批准、拒绝和执行结果都进入审计链路。', control: '只读追踪' },
    ],
  },
  patch: {
    eyebrow: '写入前审查',
    title: '补丁审查',
    summary: '在写入前阅读 diff、风险摘要和批准状态，避免看不见的文件改动。',
    metrics: [
      { label: '补丁预览', value: '多文件 diff' },
      { label: '风险摘要', value: '逐项解释', tone: 'warning' },
      { label: '批准写入', value: '等待确认', tone: 'success' },
    ],
    rows: [
      { title: '补丁预览', detail: '按文件展示新增、删除和上下文，不在这里直接写入。', control: '只读预览' },
      { title: '风险摘要', detail: '标记权限、路径、敏感信息和测试影响。', control: '人工复核', tone: 'warning' },
      { title: '批准写入', detail: '只有用户确认后，补丁才允许进入写入流程。', control: '批准门控', tone: 'success' },
    ],
  },
  audit: {
    eyebrow: '状态与恢复',
    title: '审计诊断',
    summary: '阻断、警告、提示和下一步建议按优先级展示。',
    metrics: [
      { label: '审计时间线', value: '权限与工具链路' },
      { label: '诊断中心', value: '阻断优先', tone: 'warning' },
      { label: '恢复建议', value: '人工确认', tone: 'success' },
    ],
    rows: [
      { title: '审计时间线', detail: '按时间记录权限请求、工具结果、测试反馈和恢复动作。', control: '只读查看' },
      { title: '诊断中心', detail: '阻断、警告、提示分层显示，先处理高风险项。', control: '优先级' },
      { title: '恢复建议', detail: '只给出可验证下一步，不自动执行修复。', control: '等待确认', tone: 'warning' },
    ],
  },
  validation: {
    eyebrow: '只读发布门禁',
    title: '验证发布',
    summary: '这里只展示检查结果，不执行推送、发布或打标签。',
    metrics: [
      { label: '验证门禁', value: '等待结果', tone: 'warning' },
      { label: '测试反馈', value: '结构化回填' },
      { label: '发布准备', value: '只读检查', tone: 'success' },
    ],
    rows: [
      { title: '验证门禁', detail: '汇总测试、构建、文档和中文 UI 检查结果。', control: '只读评估' },
      { title: '测试反馈', detail: '展示白名单测试回填，不接受任意 shell 命令。', control: '白名单' },
      { title: '发布准备', detail: '检查发布准备度，但不执行推送、发布或打标签。', control: '人工决定', tone: 'warning' },
    ],
  },
};

export function LiquidGlassSettingsSurface({ activeSetting }: { activeSetting: string }) {
  const surface = surfaces[activeSetting] ?? surfaces.general;

  return (
    <div className="biotSettingsSurface">
      <section className="biotSettingsHero biotLiquidBorder" aria-label={`${surface.title}概览`}>
        <GlassPill tone="success">{surface.eyebrow}</GlassPill>
        <h2>{surface.title}</h2>
        <p>{surface.summary}</p>
      </section>

      <div className="biotSettingsMetrics">
        {surface.metrics.map((metric) => (
          <GlassPanel className="biotMetricCard" key={metric.label} tone="subtle">
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <GlassPill tone={metric.tone ?? 'default'}>当前</GlassPill>
          </GlassPanel>
        ))}
      </div>

      <GlassPanel className="biotGlassCard" flow>
        {surface.rows.map((row) => (
          <div className="biotSettingRow" key={row.title}>
            <div><strong>{row.title}</strong><span>{row.detail}</span></div>
            <GlassButton>{row.control}</GlassButton>
          </div>
        ))}
      </GlassPanel>
    </div>
  );
}
