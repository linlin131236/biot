/**
 * SessionRecoveryPanel — 会话恢复体验 (M98)。
 * 展示可恢复任务、恢复摘要、风险和恢复前检查项。
 * 纯只读，不自动 resume。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface Props {
  baseUrl: string;
  api: { fetchSessionRecovery: (b: string) => Promise<Record<string, unknown>> };
}

export function SessionRecoveryPanel({ baseUrl, api }: Props) {
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchSessionRecovery(baseUrl);
        if (cancelled) return;
        setTasks(Array.isArray(raw.paused_tasks) ? raw.paused_tasks as Record<string, unknown>[] : []);
        setTotal((raw.total_paused as number) || 0);
        setPolicy((raw.recovery_policy as Record<string, unknown>) || null);
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="sessionRecoveryPanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="sessionRecoveryPanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;

  return (
    <div className="sessionRecoveryPanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>会话恢复</h2>

      {/* Paused tasks */}
      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>可恢复任务（{total}）</div>
        {tasks.length === 0 ? (
          <div style={{ color: '#888', padding: '0.5rem' }}>暂无暂停的任务。</div>
        ) : (
          tasks.map((t, i) => (
            <div key={i} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: '3px solid #e90', background: '#fffbe5', fontSize: '0.8rem',
            }}>
              <strong>{t.objective as string || '未命名任务'}</strong>
              {t.goal_id ? <span style={{ fontSize: '0.7rem', color: '#888', marginLeft: '6px' }}>ID: {t.goal_id as string}</span> : null}
            </div>
          ))
        )}
      </div>

      {/* Recovery policy */}
      {policy && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>恢复策略</div>
          <div style={{ fontSize: '0.75rem', color: '#666', background: '#f8f8f8', padding: '4px 8px', borderRadius: '3px' }}>
            {policy.summary_cn as string || '恢复策略已就绪'}
          </div>
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读会话恢复视图。不自动 resume，恢复前需重新验证权限和状态。
      </div>
    </div>
  );
}
