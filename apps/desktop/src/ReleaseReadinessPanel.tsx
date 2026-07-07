/**
 * ReleaseReadinessPanel — 发布准备页 (M95)。
 * 显示 release readiness 和 local release checklist，只读不发布。
 * 不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface ReleaseCheck {
  label?: string;
  passed?: boolean;
  reason?: string;
  suggestion?: string;
}

interface ReleaseData {
  readiness: Record<string, unknown> | null;
  checklist: Record<string, unknown> | null;
  recovery: Record<string, unknown> | null;
}

interface Props {
  baseUrl: string;
  api: {
    fetchReleaseReadiness: (baseUrl: string) => Promise<Record<string, unknown>>;
    fetchLocalChecklist: (baseUrl: string) => Promise<Record<string, unknown>>;
    fetchRecoveryPolicy: (baseUrl: string) => Promise<Record<string, unknown>>;
  };
}

export function ReleaseReadinessPanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<ReleaseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [readiness, checklist, recovery] = await Promise.all([
          api.fetchReleaseReadiness(baseUrl),
          api.fetchLocalChecklist(baseUrl),
          api.fetchRecoveryPolicy(baseUrl),
        ]);
        if (cancelled) return;
        setData({ readiness, checklist, recovery });
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="releaseReadinessPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="releaseReadinessPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="releaseReadinessPanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const ready = data.readiness?.ready === true;
  const checks: ReleaseCheck[] = Array.isArray(data.checklist?.checks)
    ? (data.checklist.checks as Record<string, unknown>[]).map((c: Record<string, unknown>) => ({
        label: (c.label as string) || '',
        passed: (c.passed as boolean) || false,
        reason: (c.reason as string) || '',
        suggestion: (c.suggestion as string) || '',
      }))
    : [];

  const blockers = checks.filter(c => !c.passed);
  const recoverySummary = data.recovery?.summary_cn as string || '';

  return (
    <div className="releaseReadinessPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>发布准备</h2>

      {/* Ready/Not Ready */}
      <div style={{
        padding: '0.5rem', marginBottom: '0.75rem', borderRadius: '4px',
        background: ready ? '#f0f7f0' : '#fff5f5',
        border: `1px solid ${ready ? '#4a4' : '#d44'}`,
        fontWeight: 600,
      }}>
        {ready ? '✅ 已准备好发布' : '❌ 尚未准备好发布'}
        {!ready && blockers.length > 0 && `（${blockers.length} 个阻断项）`}
      </div>

      {/* Checklist */}
      {checks.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>检查清单</div>
          {checks.map((c, i) => (
            <div key={i} style={{
              padding: '3px 6px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${c.passed ? '#4a4' : '#d44'}`,
              background: c.passed ? '#fafafa' : '#fff5f5',
              fontSize: '0.75rem',
            }}>
              {c.passed ? '✅' : '❌'} {c.label}
              {!c.passed && c.reason && (
                <span style={{ color: '#c44', marginLeft: '4px' }}>— {c.reason}</span>
              )}
              {!c.passed && c.suggestion && (
                <div style={{ fontSize: '0.65rem', color: '#888' }}>建议：{c.suggestion}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Recovery policy */}
      {recoverySummary && (
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.75rem' }}>
          <strong>恢复策略：</strong>{recoverySummary}
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此页面为只读发布准备检查，不提供 release/tag/push/delete 按钮。
      </div>
    </div>
  );
}
