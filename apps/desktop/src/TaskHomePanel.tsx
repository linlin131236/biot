/**
 * TaskHomePanel — 中文任务首页面板 (M91)。
 * 爸爸打开桌面的第一屏：当前目标、权限待处理、诊断风险、下一步建议。
 * 纯只读，无 push/release/delete/approve 按钮。
 * 不直接访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';
import type { TaskHomeSummary, TaskHomeEvent } from '@bolt/shared/autonomy';

interface Props {
  baseUrl: string;
  api: {
    fetchTaskHome: (baseUrl: string) => Promise<Record<string, unknown>>;
  };
}

function mapSummary(raw: Record<string, unknown>): TaskHomeSummary {
  const events: TaskHomeEvent[] = Array.isArray(raw.recent_events)
    ? (raw.recent_events as Record<string, unknown>[]).map((e: Record<string, unknown>) => ({
        code: (e.code as string) || '',
        severity: (e.severity as string) || '',
        severity_label: (e.severity_label as string) || '',
        summary: (e.summary as string) || '',
        suggestion: (e.suggestion as string) || '',
      }))
    : [];
  return {
    current_goal: (raw.current_goal as Record<string, unknown>) || null,
    unfinished_goal_count: (raw.unfinished_goal_count as number) || 0,
    pending_permission_count: (raw.pending_permission_count as number) || 0,
    blocker_count: (raw.blocker_count as number) || 0,
    warning_count: (raw.warning_count as number) || 0,
    active_task_count: (raw.active_task_count as number) || 0,
    recent_events: events,
    next_suggestions: Array.isArray(raw.next_suggestions)
      ? (raw.next_suggestions as string[])
      : [],
    updated_at: (raw.updated_at as string) || '',
  };
}

export function TaskHomePanel({ baseUrl, api }: Props) {
  const [data, setData] = useState<TaskHomeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchTaskHome(baseUrl);
        if (cancelled) return;
        setData(mapSummary(raw));
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl]);

  if (loading) return <div className="taskHomePanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="taskHomePanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="taskHomePanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;

  const goal = data.current_goal;
  const statusLabels: Record<string, string> = {
    pending: '待开始', running: '运行中', paused: '已暂停',
    completed: '已完成', failed: '已失败', stopped: '已停止', rejected: '已拒绝',
  };

  return (
    <div className="taskHomePanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>任务首页</h2>

      {/* Status overview row */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
        <StatusBadge label="目标" value={data.unfinished_goal_count} highlight={false} />
        <StatusBadge label="权限待批" value={data.pending_permission_count} highlight={data.pending_permission_count > 0} />
        <StatusBadge label="阻断" value={data.blocker_count} highlight={data.blocker_count > 0} />
        <StatusBadge label="警告" value={data.warning_count} highlight={false} />
        <StatusBadge label="活跃任务图" value={data.active_task_count} highlight={false} />
      </div>

      {/* Current goal */}
      {goal ? (
        <div style={{
          padding: '0.5rem 0.75rem', marginBottom: '0.75rem',
          background: goal.status === 'running' ? '#f0f7f0' : goal.status === 'failed' ? '#fff0f0' : '#f8f8f8',
          borderLeft: `3px solid ${goal.status === 'running' ? '#4a4' : goal.status === 'failed' ? '#d44' : '#aaa'}`,
          borderRadius: '3px',
        }}>
          <div style={{ fontWeight: 600 }}>{goal.objective as string || '未命名目标'}</div>
          <div style={{ fontSize: '0.75rem', color: '#666' }}>
            状态：{statusLabels[goal.status as string] || String(goal.status)}
            {goal.step_count != null ? ` · 已执行 ${goal.step_count} 步` : ''}
          </div>
        </div>
      ) : (
        <div style={{ padding: '0.5rem 0.75rem', marginBottom: '0.75rem', background: '#f8f8f8', borderRadius: '3px', color: '#888' }}>
          暂无进行中的目标。
        </div>
      )}

      {/* Recent events */}
      {data.recent_events.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>最近事件</div>
          {data.recent_events.map((ev, i) => (
            <div key={i} style={{
              padding: '3px 6px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${ev.severity === 'blocking' ? '#d44' : ev.severity === 'warning' ? '#e90' : '#aaa'}`,
              background: '#fafafa', fontSize: '0.75rem',
            }}>
              <span style={{ fontWeight: 500 }}>[{ev.severity_label}]</span> {ev.summary}
            </div>
          ))}
        </div>
      )}

      {/* Suggestions */}
      {data.next_suggestions.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.8rem' }}>下一步建议</div>
          {data.next_suggestions.map((s, i) => (
            <div key={i} style={{
              padding: '4px 8px', margin: '2px 0', fontSize: '0.8rem',
              color: s.includes('阻断') ? '#c44' : '#444',
              background: s.includes('阻断') ? '#fff5f5' : '#fafafa',
              borderRadius: '3px',
            }}>
              {s.includes('阻断') ? '🔴 ' : s.includes('警告') ? '🟡 ' : 'ℹ️ '}{s}
            </div>
          ))}
        </div>
      )}

      {/* Read-only note */}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读任务首页，不提供执行、批准、删除功能。
      </div>
    </div>
  );
}

function StatusBadge({ label, value, highlight }: { label: string; value: number; highlight: boolean }) {
  return (
    <span style={{
      padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem',
      background: highlight ? '#fff0f0' : '#f0f4f0',
      border: `1px solid ${highlight ? '#d88' : '#8c8'}`,
    }}>
      {label}：<strong>{value}</strong>
    </span>
  );
}
