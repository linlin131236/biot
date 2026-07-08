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
