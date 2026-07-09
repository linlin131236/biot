/**
 * GateFreezePanel — Gate 冻结控制 (M165)。
 * 冻结/解冻 Gate，查看当前状态。
 * 纯前端控制，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface Props {
  baseUrl: string;
  fetcher?: Fetcher;
  api: {
    freezeGate: (baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    unfreezeGate: (baseUrl: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchGateStatus: (baseUrl: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface GateStatus {
  frozen?: boolean;
  reason?: string;
  updated_at?: string;
}

export function GateFreezePanel({ baseUrl, fetcher = fetch, api }: Props) {
  const [status, setStatus] = useState<GateStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.fetchGateStatus(baseUrl, fetcher);
      setStatus(res as GateStatus);
    } catch (e) {
      setError(`加载状态失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, [baseUrl]);

  async function handleFreeze() {
    setError(null);
    try {
      const res = await api.freezeGate(baseUrl, { reason: reason || undefined }, fetcher);
      setStatus(res as GateStatus);
      setReason('');
    } catch (e) {
      setError(`冻结 Gate 失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function handleUnfreeze() {
    setError(null);
    try {
      const res = await api.unfreezeGate(baseUrl, fetcher);
      setStatus(res as GateStatus);
    } catch (e) {
      setError(`解冻 Gate 失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  const isFrozen = Boolean(status?.frozen);

  return (
    <div style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>Gate 冻结控制</h2>
      <div style={{ color: '#666', fontSize: '0.75rem', marginBottom: '0.75rem' }}>管理 Gate 冻结与解冻状态</div>

      {loading && <div style={{ padding: '0.5rem', color: '#888' }}>加载中…</div>}
      {error && <div style={{ padding: '0.5rem', color: '#c44' }}>{error}</div>}

      {!loading && !error && (
        <>
          <div style={{ marginBottom: '0.75rem', padding: '6px 8px', borderRadius: '4px', background: isFrozen ? '#fff3cd' : '#e6f4ea', borderLeft: '3px solid', borderColor: isFrozen ? '#e90' : '#34a853' }}>
            <div style={{ fontWeight: 600 }}>当前状态：{isFrozen ? '已冻结' : '未冻结'}</div>
            {status?.reason && <div style={{ fontSize: '0.75rem', color: '#555', marginTop: 4 }}>原因：{String(status.reason)}</div>}
            {status?.updated_at && <div style={{ fontSize: '0.75rem', color: '#555' }}>更新时间：{String(status.updated_at)}</div>}
          </div>

          {!isFrozen && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>冻结 Gate</div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <input
                  aria-label="冻结原因"
                  placeholder="冻结原因"
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                  style={{ flex: '1 1 10rem', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
                <button type="button" onClick={handleFreeze} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
                  冻结 Gate
                </button>
              </div>
            </div>
          )}

          {isFrozen && (
            <div style={{ marginBottom: '0.75rem' }}>
              <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>解冻 Gate</div>
              <button type="button" onClick={handleUnfreeze} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
                解冻 Gate
              </button>
            </div>
          )}
        </>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板仅管理 Gate 冻结状态，不提供危险操作。
      </div>
    </div>
  );
}
