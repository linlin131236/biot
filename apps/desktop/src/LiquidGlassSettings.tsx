import { useState } from 'react';
import { GlassPanel, GlassPill } from './LiquidGlassPrimitives';
import { settingItems, surfaces, type LiquidGlassSettingsProps } from './LiquidGlassSettingsData';
import { DiagnosticsFeedbackPanel } from './DiagnosticsFeedbackPanel';


function desktopDiagnosticsApi() {
  const bolt = (window as unknown as { bolt?: {
    diagnostics?: {
      exportSummary: () => Promise<string>;
      openDir: () => Promise<void>;
      setEnabled: (enabled: boolean) => Promise<void>;
      getEnabled: () => Promise<boolean>;
    };
    update?: {
      status: () => Promise<Record<string, unknown>>;
      check: (manifestUrl?: string) => Promise<Record<string, unknown>>;
    };
  } }).bolt;
  return {
    exportSummary: async () => {
      if (!bolt?.diagnostics?.exportSummary) {
        return JSON.stringify({ upload: 'disabled_by_default', events: [], note: 'diagnostics bridge unavailable' }, null, 2);
      }
      return bolt.diagnostics.exportSummary();
    },
    openDiagnosticsDir: async () => {
      await bolt?.diagnostics?.openDir?.();
    },
    setCollectionEnabled: async (enabled: boolean) => {
      await bolt?.diagnostics?.setEnabled?.(enabled);
    },
    getCollectionEnabled: async () => {
      if (!bolt?.diagnostics?.getEnabled) return true;
      return bolt.diagnostics.getEnabled();
    },
  };
}

export function LiquidGlassSettings({ activeSetting, onBack, setActiveSetting, settings, onSaveTheme }: LiquidGlassSettingsProps) {
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  async function handleSaveTheme(nextTheme: string) {
    // Delegate to parent which uses authenticated fetcher
    await onSaveTheme(nextTheme);
    setSaveMessage('设置已保存');
    setTimeout(() => setSaveMessage(null), 2000);
  }

  const surface = surfaces[activeSetting] ?? surfaces.general;
  const realThemeLabel = settings?.theme === 'light' ? '浅色' : '深色';
  const apiKeyLabel = settings?.has_api_key ? '已配置' : '未配置';
  const apiKeyTone = settings?.has_api_key ? 'success' : 'warning';

  const effectiveMetrics = activeSetting === 'general' ? [
    { label: '主题', value: realThemeLabel, tone: settings?.theme === 'light' ? 'default' as const : 'success' as const },
    { label: '语言', value: settings?.language === 'zh-CN' ? '简体中文' : settings?.language ?? '简体中文' },
    { label: '启动页', value: 'Agent 工作台' },
  ] : activeSetting === 'model' ? [
    { label: '连接方式', value: 'OpenAI 兼容' },
    { label: '密钥状态', value: apiKeyLabel, tone: apiKeyTone },
    { label: '默认模型', value: '用户选择' },
  ] : surface.metrics;

  const effectiveRows = activeSetting === 'general' ? [
    { title: '界面主题', detail: '深浅色液态玻璃主题保持同一套安全信息层级。', control: realThemeLabel, tone: settings?.theme === 'light' ? 'default' : 'success' },
    { title: '界面语言', detail: '所有用户可见文字使用中文，面向公开产品表达。', control: settings?.language === 'zh-CN' ? '简体中文' : (settings?.language ?? '简体中文') },
    { title: '启动时打开', detail: '启动后默认进入任务驾驶舱，设置中心保留在侧边导航。', control: 'Agent 工作台' },
    { title: '本地 Agent Core', detail: '由 Bolt 桌面端自动管理，用户不可配置地址。', control: '本地 Agent Core · 由 Bolt 自动管理', tone: 'success' },
    { title: '权限模式', detail: '写入、apply、恢复前都需要用户确认。', control: '写入需批准', tone: 'warning' },
  ] : activeSetting === 'model' ? [
    { title: '提供方', detail: '模型供应商和 Base URL 由本地配置管理。', control: 'OpenAI 兼容' },
    { title: 'API 密钥', detail: '只显示是否已配置，保存后立即清空输入框。', control: '仅状态可见', tone: apiKeyTone },
    { title: '模型选择', detail: '聊天时使用当前选择的模型，不自动切换到未知供应商。', control: '手动选择' },
  ] : surface.rows;

  return (
    <div className="biotSettings">
      <aside className="biotSettingsNav">
        <button type="button" className="biotBackButton" onClick={onBack}>返回工作区</button>
        {settingItems.map((item) => (
          <button
            type="button"
            key={item.id}
            className={activeSetting === item.id ? 'active' : ''}
            onClick={() => setActiveSetting(item.id)}
          >
            {item.label}
          </button>
        ))}
      </aside>

      <section className="biotSettingsContent">
        <div className="biotSettingsHeader">
          <div>
            <h1>液态玻璃设置中心</h1>
            <p>管理 Biot 的界面、模型、技能、子智能体和本地安全边界。</p>
          </div>
          <div className="biotStatusPills" aria-label="当前设置状态">
            <span><i /> 设置已保存</span>
            <span><i /> 本地配置</span>
            <span><i /> 权限安全</span>
            {saveMessage ? <span><i /> {saveMessage}</span> : null}
          </div>
        </div>

        {activeSetting === 'general' && settings ? (
          <div className="biotSettingsSurface">
            <section className="biotSettingsHero biotLiquidBorder" aria-label="常规设置概览">
              <GlassPill tone="success">{surface.eyebrow}</GlassPill>
              <h2>{surface.title}</h2>
              <p>{surface.summary}</p>
            </section>

            <div className="biotSettingsMetrics">
              {effectiveMetrics.map((metric) => (
                <GlassPanel className="biotMetricCard" key={metric.label} tone="subtle">
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <GlassPill tone={metric.tone ?? 'default'}>当前</GlassPill>
                </GlassPanel>
              ))}
            </div>

            <GlassPanel className="biotGlassCard" flow>
              {effectiveRows.map((row) => (
                <div className="biotSettingRow" key={row.title}>
                  <div><strong>{row.title}</strong><span>{row.detail}</span></div>
                  <GlassPill className="biotSettingBadge" tone={row.tone ?? 'default'}>{row.control}</GlassPill>
                </div>
              ))}
            </GlassPanel>

            <GlassPanel className="biotGlassCard" flow>
              <div className="biotSettingRow">
                <div><strong>切换主题</strong><span>切换深色/浅色液态玻璃主题，设置将持久化保存。</span></div>
                <div className="biotThemeToggle">
                  <button type="button" onClick={() => handleSaveTheme('dark')} className={settings.theme === 'dark' ? 'active' : ''}>深色</button>
                  <button type="button" onClick={() => handleSaveTheme('light')} className={settings.theme === 'light' ? 'active' : ''}>浅色</button>
                </div>
              </div>
            </GlassPanel>
          </div>
        ) : activeSetting === 'diagnostics' ? (
          <div className="biotSettingsSurface">
            <DiagnosticsFeedbackPanel api={desktopDiagnosticsApi()} />
            <GlassPanel className="biotGlassCard" flow>
              <div className="biotSettingRow">
                <div><strong>自动更新</strong><span>生产更新通道默认关闭；仅允许 allowlist HTTPS 与签名清单。</span></div>
                <GlassPill className="biotSettingBadge" tone="warning">默认关闭</GlassPill>
              </div>
            </GlassPanel>
          </div>
        ) : activeSetting === 'model' && settings ? (
          <div className="biotSettingsSurface">
            <section className="biotSettingsHero biotLiquidBorder" aria-label="模型提供方概览">
              <GlassPill tone="success">{surface.eyebrow}</GlassPill>
              <h2>{surface.title}</h2>
              <p>{surface.summary}</p>
            </section>

            <div className="biotSettingsMetrics">
              {effectiveMetrics.map((metric) => (
                <GlassPanel className="biotMetricCard" key={metric.label} tone="subtle">
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                  <GlassPill tone={metric.tone ?? 'default'}>当前</GlassPill>
                </GlassPanel>
              ))}
            </div>

            <GlassPanel className="biotGlassCard" flow>
              {effectiveRows.map((row) => (
                <div className="biotSettingRow" key={row.title}>
                  <div><strong>{row.title}</strong><span>{row.detail}</span></div>
                  <GlassPill className="biotSettingBadge" tone={row.tone ?? 'default'}>{row.control}</GlassPill>
                </div>
              ))}
            </GlassPanel>
          </div>
        ) : (
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
                  <GlassPill className="biotSettingBadge" tone={row.tone ?? 'default'}>{row.control}</GlassPill>
                </div>
              ))}
            </GlassPanel>
          </div>
        )}
      </section>
    </div>
  );
}
