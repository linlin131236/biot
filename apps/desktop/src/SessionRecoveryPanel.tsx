/**
 * 会话恢复面板：只读展示可恢复任务与恢复策略，不自动 resume。
 */
import { useEffect, useMemo, useState } from 'react';

interface Props {
  api: { fetchSessionRecovery: () => Promise<Record<string, unknown>> };
}

export function SessionRecoveryPanel({ api }: Props) {
  const [tasks, setTasks] = useState<Record<string, unknown>[]>([]);
  const [policy, setPolicy] = useState<Record<string, unknown> | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchSessionRecovery();
        if (cancelled) return;
        setTasks(Array.isArray(raw.paused_tasks) ? raw.paused_tasks as Record<string, unknown>[] : []);
        setTotal(typeof raw.total_paused === 'number' ? raw.total_paused : 0);
        setPolicy((raw.recovery_policy as Record<string, unknown>) || null);
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [api]);

  const policyText = useMemo(() => formatPolicy(policy), [policy]);

  if (loading) return <div className="sessionRecoveryPanel" style={panelStyle}>加载中...</div>;
  if (error) return <div className="sessionRecoveryPanel" style={{ ...panelStyle, color: '#c44' }}>{error}</div>;

  return (
    <div className="sessionRecoveryPanel" style={{ ...panelStyle, fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>会话恢复</h2>

      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>可恢复任务（{total}）</div>
        {tasks.length === 0 ? (
          <div style={{ color: '#888', padding: '0.5rem' }}>暂无暂停的任务。</div>
        ) : (
          tasks.map((task, index) => (
            <div key={`${String(task.goal_id || index)}-${String(task.objective || '')}`} style={{
              padding: '4px 8px',
              margin: '2px 0',
              borderRadius: '3px',
              borderLeft: '3px solid #e90',
              background: '#fffbe5',
              fontSize: '0.8rem',
            }}>
              <strong>{String(task.objective || '未命名任务')}</strong>
              {task.goal_id ? <span style={{ fontSize: '0.7rem', color: '#888', marginLeft: '6px' }}>ID: {String(task.goal_id)}</span> : null}
            </div>
          ))
        )}
      </div>

      {policy && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>恢复策略</div>
          <div style={{ fontSize: '0.75rem', color: '#666', background: '#f8f8f8', padding: '4px 8px', borderRadius: '3px' }}>
            {policyText}
          </div>
        </div>
      )}

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#777', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读会话恢复视图。不自动 resume，恢复前必须重新验证权限和状态。
      </div>
    </div>
  );
}

const panelStyle = { padding: '0.75rem', color: '#666' };

function formatPolicy(policy: Record<string, unknown> | null): string {
  if (!policy) return '';
  if (typeof policy.summary_cn === 'string') return policy.summary_cn;
  if (typeof policy.total === 'number') return `已加载 ${policy.total} 条恢复策略`;
  if (typeof policy.disclaimer === 'string') return policy.disclaimer;
  return '恢复策略已就绪';
}
