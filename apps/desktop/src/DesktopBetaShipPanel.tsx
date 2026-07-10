import { useEffect, useState } from 'react';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface ShipCheck {
  name: string;
  passed: boolean;
  detail: string;
  severity: string;
}

interface ShipResult {
  ready?: boolean;
  all_passed?: boolean;
  total?: number;
  passed_count?: number;
  failed_count?: number;
  p1_failures?: string[];
  warnings?: string[];
  next_step?: string;
  checks?: ShipCheck[];
}

interface Props {
  fetcher?: Fetcher;
  api: {
    fetchBetaShip: (fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

export function DesktopBetaShipPanel({ fetcher, api }: Props) {
  const [result, setResult] = useState<ShipResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.fetchBetaShip(fetcher)
      .then(data => {
        if (!cancelled) setResult(data as ShipResult);
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => { cancelled = true; };
  }, [fetcher, api]);

  const ready = Boolean(result?.ready ?? result?.all_passed);
  const checks = result?.checks ?? [];

  return (
    <section className="liquid-glass-panel" aria-label="桌面 Beta 发布候选" style={{ padding: '0.85rem' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1rem' }}>桌面 Beta 发布候选</h2>
          <p style={{ margin: '0.25rem 0 0', color: 'var(--muted)', fontSize: '0.78rem' }}>
            M171-M180 最终收口门禁，只读检查，不自动发布。
          </p>
        </div>
        {result && (
          <strong style={{ color: ready ? 'var(--success)' : 'var(--danger)' }}>
            {ready ? '可以进入人工复审' : '存在阻断项'}
          </strong>
        )}
      </header>

      {error && <div role="alert" style={{ marginTop: '0.75rem', color: 'var(--danger)' }}>加载失败：{error}</div>}
      {!result && !error && <div style={{ marginTop: '0.75rem', color: 'var(--muted)' }}>正在检查桌面 Beta 状态...</div>}

      {result && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.5rem', marginTop: '0.75rem' }}>
            <Metric label="总检查" value={String(result.total ?? checks.length)} />
            <Metric label="通过" value={String(result.passed_count ?? checks.filter(item => item.passed).length)} />
            <Metric label="阻断" value={String(result.failed_count ?? checks.filter(item => !item.passed).length)} />
          </div>

          {Boolean(result.p1_failures?.length) && (
            <div style={{ marginTop: '0.75rem', padding: '0.6rem', border: '1px solid var(--danger)', borderRadius: 8 }}>
              <strong>阻断项</strong>
              <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.1rem' }}>
                {result.p1_failures?.map(item => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}

          <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.45rem' }}>
            {checks.map(item => (
              <div key={item.name} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '0.55rem 0.65rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                  <strong>{item.name}</strong>
                  <span>{item.passed ? '通过' : '未通过'}</span>
                </div>
                <div style={{ color: 'var(--muted)', fontSize: '0.76rem', marginTop: '0.2rem' }}>{item.detail}</div>
              </div>
            ))}
          </div>

          {result.next_step && (
            <div style={{ marginTop: '0.75rem', color: 'var(--muted)', fontSize: '0.78rem' }}>
              下一步：{result.next_step}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: '0.55rem' }}>
      <div style={{ color: 'var(--muted)', fontSize: '0.72rem' }}>{label}</div>
      <div style={{ fontSize: '1.05rem', fontWeight: 700 }}>{value}</div>
    </div>
  );
}
