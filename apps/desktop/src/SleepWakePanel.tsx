/**
 * SleepWakePanel — Agent 待机/唤醒控制 (M164)。
 * 提供 sleep、wake、状态查看和历史记录。
 * 纯前端控制，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface SleepWakeApi {
  sleep: (baseUrl: string, payload: Record<string, unknown>, fetcher?: Fetcher) => Promise<Record<string, unknown>>;
  wake: (baseUrl: string, payload: Record<string, unknown>, fetcher?: Fetcher) => Promise<Record<string, unknown>>;
  fetchStatus: (baseUrl: string, fetcher?: Fetcher) => Promise<Record<string, unknown>>;
}

interface Props {
  baseUrl: string;
  api: SleepWakeApi;
}

interface HistoryEntry {
  action: string;
  state?: string;
  is_sleeping?: boolean;
  at: string;
}

export function SleepWakePanel({ baseUrl, api }: Props) {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState('60');
  const [reason, setReason] = useState('');
  const [trigger, setTrigger] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.fetchStatus(baseUrl);
      setStatus(res);
    } catch (e) {
      setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStatus();
  }, [baseUrl]);

  async function handleSleep() {
    setError(null);
    try {
      const res = await api.sleep(baseUrl, {
        duration_seconds: Number(duration) || 60,
        reason: reason || undefined,
      });
      setStatus(res);
      setHistory(prev => [{ action: 'sleep', state: String(res.state ?? ''), is_sleeping: Boolean(res.is_sleeping), at: new Date().toLocaleString() }, ...prev].slice(0, 5));
    } catch (e) {
      setError(`进入待机失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  async function handleWake() {
    setError(null);
    try {
      const res = await api.wake(baseUrl, { trigger: trigger || undefined });
      setStatus(res);
      setHistory(prev => [{ action: 'wake', state: String(res.state ?? ''), is_sleeping: Boolean(res.is_sleeping), at: new Date().toLocaleString() }, ...prev].slice(0, 5));
    } catch (e) {
      setError(`唤醒失败：${e instanceof Error ? e.message : String(e)}`);
    }
  }

  const currentState = String(status?.state ?? 'awake');
  const isSleeping = Boolean(status?.is_sleeping);

  return (
    <div className="sleepWakePanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>待机控制</h2>
      <div style={{ color: '#666', fontSize: '0.75rem', marginBottom: '0.75rem' }}>管理 Agent 待机/唤醒生命周期</div>

      {loading && <div style={{ padding: '0.5rem', color: '#888' }}>加载中…</div>}
      {error && <div style={{ padding: '0.5rem', color: '#c44' }}>{error}</div>}

      {!loading && !error && (
        <>
          <div style={{ marginBottom: '0.75rem', padding: '6px 8px', borderRadius: '4px', background: isSleeping ? '#fff3cd' : '#e6f4ea', borderLeft: '3px solid', borderColor: isSleeping ? '#e90' : '#34a853' }}>
            <div style={{ fontWeight: 600 }}>当前状态：{currentState}</div>
            <div style={{ fontSize: '0.75rem', color: '#555' }}>is_sleeping：{isSleeping ? 'true' : 'false'}</div>
          </div>

          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>进入待机</div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                aria-label="待机时长"
                placeholder="时长（秒）"
                value={duration}
                onChange={e => setDuration(e.target.value)}
                style={{ width: '8rem', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
              <input
                aria-label="待机原因"
                placeholder="原因"
                value={reason}
                onChange={e => setReason(e.target.value)}
                style={{ flex: '1 1 10rem', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
              <button type="button" onClick={handleSleep} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
                进入待机
              </button>
            </div>
          </div>

          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>唤醒</div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                aria-label="唤醒触发原因"
                placeholder="触发原因"
                value={trigger}
                onChange={e => setTrigger(e.target.value)}
                style={{ flex: '1 1 10rem', padding: '6px 8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
              <button type="button" onClick={handleWake} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
                唤醒
              </button>
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>最近操作</div>
            {history.length === 0 ? (
              <div style={{ color: '#888', padding: '0.4rem 0' }}>暂无记录。</div>
            ) : (
              <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                {history.map((item, idx) => (
                  <li key={idx} style={{ marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600 }}>{item.action === 'sleep' ? '待机' : '唤醒'}</span>
                    <span style={{ color: '#666', marginLeft: '6px' }}>{item.state || '未知状态'}</span>
                    <span style={{ color: '#999', fontSize: '0.7rem', marginLeft: '6px' }}>{item.at}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板仅管理待机/唤醒生命周期，不提供危险操作。
      </div>
    </div>
  );
}
