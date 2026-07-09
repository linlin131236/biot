/**
 * 发布准备度面板：只读展示，不提供 release/tag/push/delete 操作。
 */
import { useEffect, useMemo, useState } from 'react';

interface NormalizedCheck {
  label: string;
  passed: boolean;
  reason: string;
  suggestion: string;
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
        if (!cancelled) setData({ readiness, checklist, recovery });
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [api, baseUrl]);

  const checks = useMemo(() => normalizeChecks(data?.checklist), [data?.checklist]);
  const blockers = checks.filter((check) => !check.passed);
  const ready = data?.readiness?.ready === true || (data?.checklist?.ready === true && blockers.length === 0);
  const recoverySummary = recoveryText(data?.recovery);

  if (loading) return <div className="releaseReadinessPanel" style={panelStyle}>加载中...</div>;
  if (error) return <div className="releaseReadinessPanel" style={{ ...panelStyle, color: '#c44' }}>{error}</div>;
  if (!data) return <div className="releaseReadinessPanel" style={panelStyle}>暂无数据。</div>;

  return (
    <div className="releaseReadinessPanel" style={{ ...panelStyle, fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>发布准备度</h2>

      <div style={{
        padding: '0.5rem',
        marginBottom: '0.75rem',
        borderRadius: '4px',
        background: ready ? '#f0f7f0' : '#fff5f5',
        border: `1px solid ${ready ? '#4a4' : '#d44'}`,
        fontWeight: 600,
      }}>
        {ready ? '已准备好发布' : '尚未准备好发布'}
        {!ready && blockers.length > 0 && `：${blockers.length} 个阻断项`}
      </div>

      {checks.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>检查清单</div>
          {checks.map((check) => (
            <div key={check.label} style={{
              padding: '3px 6px',
              margin: '2px 0',
              borderRadius: '3px',
              borderLeft: `3px solid ${check.passed ? '#4a4' : '#d44'}`,
              background: check.passed ? '#fafafa' : '#fff5f5',
              fontSize: '0.75rem',
            }}>
              {check.passed ? '通过' : '阻断'}：{check.label}
              {!check.passed && check.reason && (
                <span style={{ color: '#c44', marginLeft: '4px' }}>- {check.reason}</span>
              )}
              {!check.passed && check.suggestion && (
                <div style={{ fontSize: '0.65rem', color: '#666' }}>建议：{check.suggestion}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {recoverySummary && (
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.75rem' }}>
          <strong>恢复策略：</strong>{recoverySummary}
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#777', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此页面为只读发布准备检查，不提供 release/tag/push/delete 按钮。
      </div>
    </div>
  );
}

const panelStyle = { padding: '0.75rem', color: '#666' };

function normalizeChecks(checklist: Record<string, unknown> | null | undefined): NormalizedCheck[] {
  const rawItems = Array.isArray(checklist?.items)
    ? checklist.items as Record<string, unknown>[]
    : Array.isArray(checklist?.checks)
      ? checklist.checks as Record<string, unknown>[]
      : [];

  return rawItems.map((item) => {
    const status = item.status as string | undefined;
    const passed = typeof item.passed === 'boolean' ? item.passed : status === 'pass';
    return {
      label: String(item.label || item.code || '未命名检查项'),
      passed,
      reason: String(item.reason || item.detail || ''),
      suggestion: String(item.suggestion || item.recommendation || ''),
    };
  });
}

function recoveryText(recovery: Record<string, unknown> | null | undefined): string {
  if (!recovery) return '';
  if (typeof recovery.summary_cn === 'string') return recovery.summary_cn;
  if (typeof recovery.disclaimer === 'string') return recovery.disclaimer;
  if (typeof recovery.total === 'number') return `已加载 ${recovery.total} 条恢复策略`;
  return '';
}
