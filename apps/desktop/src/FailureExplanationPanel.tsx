/**
 * FailureExplanationPanel — 失败解释体验 (M97)。
 * 展示失败分类和失败记忆，每条有中文原因/影响/建议。
 * 纯只读，不自动 retry/fix。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface FailureItem {
  id: string; category: string; category_cn: string; summary: string;
  suggestion: string; retryable: boolean; occurred_at: string;
}

interface Props {
  api: { fetchFailureExplanation: () => Promise<Record<string, unknown>> };
}

export function FailureExplanationPanel({ api }: Props) {
  const [items, setItems] = useState<FailureItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchFailureExplanation();
        if (cancelled) return;
        setItems(Array.isArray(raw.failures) ? (raw.failures as Record<string, unknown>[]).map((f: Record<string, unknown>) => ({
          id: (f.id as string) || '', category: (f.category as string) || '',
          category_cn: (f.category_cn as string) || '', summary: (f.summary as string) || '',
          suggestion: (f.suggestion as string) || '', retryable: (f.retryable as boolean) || false,
          occurred_at: (f.occurred_at as string) || '',
        })) : []);
        setTotal((raw.total as number) || 0);
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div className="failureExplanationPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="failureExplanationPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;

  return (
    <div className="failureExplanationPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>失败解释</h2>
      <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.5rem' }}>共 {total} 条失败记录</div>
      {items.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>暂无失败记录。</div>
      ) : (
        <div style={{ maxHeight: '30vh', overflowY: 'auto' }}>
          {items.map((f, i) => (
            <div key={f.id || i} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${f.retryable ? '#e90' : '#d44'}`,
              background: '#fff8f8', fontSize: '0.8rem',
            }}>
              <div>
                <span style={{ fontWeight: 600, marginRight: '6px' }}>[{f.category_cn || f.category}]</span>
                {f.summary}
                {f.retryable ? <span style={{ fontSize: '0.65rem', color: '#e90', marginLeft: '4px' }}>可重试</span> : <span style={{ fontSize: '0.65rem', color: '#d44', marginLeft: '4px' }}>需人工确认</span>}
              </div>
              {f.suggestion && <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px' }}>建议：{f.suggestion}</div>}
              {f.occurred_at && <div style={{ fontSize: '0.65rem', color: '#aaa' }}>{f.occurred_at}</div>}
            </div>
          ))}
        </div>
      )}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读失败解释视图。不自动 retry，不自动 fix，高风险失败必须人工确认。
      </div>
    </div>
  );
}
