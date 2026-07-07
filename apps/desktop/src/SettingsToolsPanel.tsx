/**
 * SettingsToolsPanel — 设置/模型/工具面板 (M99)。
 * 显示模型配置、预算、工具策略和风险分类。
 * 不存储 secret 明文，不显示 token/key，不执行工具。
 * 不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface Props {
  baseUrl: string;
  api: { fetchSettingsTools: (b: string) => Promise<Record<string, unknown>> };
}

export function SettingsToolsPanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchSettingsTools(baseUrl);
        if (cancelled) return;
        setData(raw);
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="settingsToolsPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="settingsToolsPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="settingsToolsPanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const model = data.model_config as Record<string, unknown> || {};
  const tool = data.tool_policy as Record<string, unknown> || {};
  const budget = data.budget as Record<string, unknown> || {};

  return (
    <div className="settingsToolsPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>设置与工具</h2>

      {/* Model */}
      <div style={{ marginBottom: '0.75rem', padding: '6px', background: '#f8f8f8', borderRadius: '4px' }}>
        <div style={{ fontWeight: 600, fontSize: '0.8rem' }}>模型配置</div>
        <div style={{ fontSize: '0.75rem', color: '#666' }}>提供商：{model.provider as string || '未知'}</div>
        <div style={{ fontSize: '0.75rem', color: '#666' }}>状态：{model.status as string || '未知'}</div>
      </div>

      {/* Budget */}
      {Object.keys(budget).length > 0 && (
        <div style={{ marginBottom: '0.75rem', padding: '6px', background: '#f8f8f8', borderRadius: '4px' }}>
          <div style={{ fontWeight: 600, fontSize: '0.8rem' }}>预算</div>
          {Object.entries(budget).map(([k, v]) => (
            <div key={k} style={{ fontSize: '0.75rem', color: '#666' }}>{k}：{String(v)}</div>
          ))}
        </div>
      )}

      {/* Tools */}
      <div style={{ marginBottom: '0.75rem', padding: '6px', background: '#f8f8f8', borderRadius: '4px' }}>
        <div style={{ fontWeight: 600, fontSize: '0.8rem' }}>工具策略</div>
        <div style={{ fontSize: '0.75rem', color: '#666' }}>模式：{tool.mode as string || '未知'}</div>
        <div style={{ fontSize: '0.75rem', color: '#666' }}>{tool.description as string || ''}</div>
        <div style={{ fontSize: '0.7rem', color: '#999', marginTop: '4px' }}>
          注意：危险工具（写文件、执行命令）需 PermissionGate 审批。
        </div>
      </div>

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读配置视图。不显示 secret/token/key，不提供执行入口。
      </div>
    </div>
  );
}
