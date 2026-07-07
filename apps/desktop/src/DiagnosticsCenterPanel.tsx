/**
 * DiagnosticsCenterPanel — 诊断中心 (M94)。
 * 统一展示阻断、警告、提示，每条有中文原因/影响/建议下一步。
 * 纯只读，不自动修复。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface DiagnosticItem {
  code?: string;
  severity?: string;
  severity_label?: string;
  summary?: string;
  suggestion?: string;
}

interface DiagnosticsData {
  diagnostics: DiagnosticItem[];
  integrity: DiagnosticItem[];
  total_blockers: number;
  total_warnings: number;
  total_infos: number;
}

interface Props {
  baseUrl: string;
  api: {
    fetchDiagnosticsCenter: (baseUrl: string) => Promise<Record<string, unknown>>;
  };
}

function mapData(raw: Record<string, unknown>): DiagnosticsData {
  const mapList = (arr: unknown): DiagnosticItem[] =>
    Array.isArray(arr) ? (arr as Record<string, unknown>[]).map((d: Record<string, unknown>) => ({
      code: (d.code as string) || '',
      severity: (d.severity as string) || '',
      severity_label: (d.severity_label as string) || '',
      summary: (d.summary as string) || '',
      suggestion: (d.suggestion as string) || '',
    })) : [];

  const diags = mapList(raw.diagnostics);
  const integ = mapList(raw.integrity);

  return {
    diagnostics: diags,
    integrity: integ,
    total_blockers: (raw.total_blockers as number) || 0,
    total_warnings: (raw.total_warnings as number) || 0,
    total_infos: (raw.total_infos as number) || 0,
  };
}

export function DiagnosticsCenterPanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSev, setFilterSev] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchDiagnosticsCenter(baseUrl);
        if (cancelled) return;
        setData(mapData(raw));
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="diagnosticsCenterPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="diagnosticsCenterPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="diagnosticsCenterPanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const allItems = [...data.diagnostics, ...data.integrity.map(i => ({ ...i, code: `[完整性] ${i.code}` }))];
  const filtered = filterSev === 'all' ? allItems : allItems.filter(i => i.severity === filterSev);

  const sevColor = (s?: string) => s === 'blocking' ? '#d44' : s === 'warning' ? '#e90' : '#888';
  const sevBg = (s?: string) => s === 'blocking' ? '#fff5f5' : s === 'warning' ? '#fffbe5' : '#fafafa';

  return (
    <div className="diagnosticsCenterPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>诊断中心</h2>

      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', background: '#fff0f0', border: '1px solid #d88' }}>
          阻断：<strong>{data.total_blockers}</strong>
        </span>
        <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', background: '#fffbe5', border: '1px solid #e90' }}>
          警告：<strong>{data.total_warnings}</strong>
        </span>
        <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', background: '#f0f4f0', border: '1px solid #8c8' }}>
          提示：<strong>{data.total_infos}</strong>
        </span>
      </div>

      {allItems.length > 0 && (
        <div style={{ marginBottom: '0.5rem' }}>
          <select value={filterSev} onChange={e => setFilterSev(e.target.value)} style={{ padding: '2px 4px', fontSize: '0.8rem' }}>
            <option value="all">全部级别</option>
            <option value="blocking">阻断</option>
            <option value="warning">警告</option>
            <option value="info">提示</option>
          </select>
        </div>
      )}

      {filtered.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>暂无诊断项。</div>
      ) : (
        <div style={{ maxHeight: '30vh', overflowY: 'auto' }}>
          {filtered.map((item, i) => (
            <div key={i} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${sevColor(item.severity)}`,
              background: sevBg(item.severity), fontSize: '0.8rem',
            }}>
              <div>
                <span style={{ fontWeight: 600 }}>[{item.severity_label || item.severity}]</span>
                <span style={{ marginLeft: '6px' }}>{item.summary}</span>
              </div>
              {item.suggestion && (
                <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px' }}>
                  建议：{item.suggestion}
                </div>
              )}
              <div style={{ fontSize: '0.65rem', color: '#aaa' }}>{item.code}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读诊断视图。区分"必须修复"和"可接受风险"，不自动修复。
      </div>
    </div>
  );
}
