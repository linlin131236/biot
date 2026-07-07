/**
 * MultiTaskQueuePanel — 多任务队列 (M96)。
 * 统一展示任务闭环、目标、计划图，支持状态/风险筛选。
 * 纯只读，不自动启动/继续任务。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface TaskItem {
  type: string; id: string; title: string; status: string; risk: string;
}

interface QueueData {
  tasks: TaskItem[];
  total: number;
  closures_count: number;
  goals_count: number;
  graphs_count: number;
}

interface Props {
  baseUrl: string;
  api: { fetchMultiTaskQueue: (b: string) => Promise<Record<string, unknown>> };
}

const TYPE_CN: Record<string, string> = { closure: '闭环', goal: '目标', graph: '任务图' };
const STATUS_CN: Record<string, string> = {
  pending: '待开始', running: '运行中', completed: '已完成', failed: '已失败',
  paused: '已暂停', active: '活跃', stopped: '已停止',
};

export function MultiTaskQueuePanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<QueueData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchMultiTaskQueue(baseUrl);
        if (cancelled) return;
        const tasks: TaskItem[] = Array.isArray(raw.tasks)
          ? (raw.tasks as Record<string, unknown>[]).map((t: Record<string, unknown>) => ({
              type: (t.type as string) || '', id: (t.id as string) || '',
              title: (t.title as string) || '', status: (t.status as string) || '',
              risk: (t.risk as string) || 'low',
            }))
          : [];
        setData({
          tasks, total: (raw.total as number) || 0,
          closures_count: (raw.closures_count as number) || 0,
          goals_count: (raw.goals_count as number) || 0,
          graphs_count: (raw.graphs_count as number) || 0,
        });
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="multiTaskQueuePanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="multiTaskQueuePanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="multiTaskQueuePanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const filtered = filterStatus === 'all' ? data.tasks : data.tasks.filter(t => t.status === filterStatus);

  return (
    <div className="multiTaskQueuePanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>多任务队列</h2>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', fontSize: '0.75rem', color: '#666' }}>
        <span>闭环 {data.closures_count}</span><span>目标 {data.goals_count}</span><span>任务图 {data.graphs_count}</span>
        <span>共 {data.total} 项</span>
      </div>
      {data.tasks.length > 0 && (
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ padding: '2px 4px', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
          <option value="all">全部状态</option>
          <option value="running">运行中</option>
          <option value="pending">待开始</option>
          <option value="completed">已完成</option>
          <option value="failed">已失败</option>
          <option value="paused">已暂停</option>
        </select>
      )}
      {filtered.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>暂无匹配的任务。</div>
      ) : (
        <div style={{ maxHeight: '30vh', overflowY: 'auto' }}>
          {filtered.map((t, i) => (
            <div key={`${t.type}-${t.id || i}`} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${t.status === 'failed' ? '#d44' : t.status === 'completed' ? '#4a4' : t.status === 'running' ? '#48f' : '#aaa'}`,
              background: '#fafafa', fontSize: '0.8rem',
            }}>
              <span style={{ fontSize: '0.7rem', color: '#888', marginRight: '6px' }}>[{TYPE_CN[t.type] || t.type}]</span>
              <strong>{t.title}</strong>
              <span style={{ marginLeft: '8px', fontSize: '0.7rem', color: '#666' }}>{STATUS_CN[t.status] || t.status}</span>
            </div>
          ))}
        </div>
      )}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读任务队列视图，不自动启动任务，不自动继续未授权任务。
      </div>
    </div>
  );
}
