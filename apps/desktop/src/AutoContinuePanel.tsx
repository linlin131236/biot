/**
 * AutoContinuePanel — 自动继续 (M169)。
 * 开启/关闭自动继续，展示当前状态。
 * 纯前端控制，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface Props {
  fetcher?: Fetcher;
  api: {
    autoContinue: (payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchAutoContinueStatus: (fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface AutoContinueStatus {
  enabled?: boolean;
  updated_at?: string;
}

export function AutoContinuePanel({ fetcher, api }: Props) {
  const [status, setStatus] = useState<AutoContinueStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.fetchAutoContinueStatus(fetcher);
      setStatus(res as AutoContinueStatus);
    } catch (e) {
      setError(`加载状态失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, []);

  async function handleToggle() {
    setError(null);
    const nextEnabled = !(status?.enabled ?? false);
    try {
      const res = await api.autoContinue({ enabled: nextEnabled }, fetcher);
      setStatus(res as AutoContinueStatus);
    } catch (e) {
      setError(`切换失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  const isEnabled = Boolean(status?.enabled);

  return (
    <div style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>自动继续</h2>
      <div style={{ color: '#666', fontSize: '0.75rem', marginBottom: '0.75rem' }}>管理编排流程自动继续开关</div>

      {loading && <div style={{ padding: '0.5rem', color: '#888' }}>加载中…</div>}
      {error && <div style={{ padding: '0.5rem', color: '#c44' }}>{error}</div>}

      {!loading && !error && (
        <>
          <div style={{ marginBottom: '0.75rem', padding: '6px 8px', borderRadius: '4px', background: isEnabled ? '#e6f4ea' : '#fff3cd', borderLeft: '3px solid', borderColor: isEnabled ? '#34a853' : '#e90' }}>
            <div style={{ fontWeight: 600 }}>自动继续：{isEnabled ? '已开启' : '已关闭'}</div>
            {status?.updated_at && <div style={{ fontSize: '0.75rem', color: '#555' }}>更新时间：{String(status.updated_at)}</div>}
          </div>

          <button type="button" onClick={handleToggle} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
            {isEnabled ? '关闭自动继续' : '开启自动继续'}
          </button>
        </>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板仅管理自动继续状态，不提供危险操作。
      </div>
    </div>
  );
}
