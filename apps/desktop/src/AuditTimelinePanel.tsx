/**
 * AuditTimelinePanel — 审计时间线视图 (M93)。
 * 展示任务从 queue→handoff→permission→closure→evidence 全过程。
 * 纯只读，无执行按钮。不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface TimelineEvent {
  id?: string;
  source?: string;
  status?: string;
  label?: string;
  summary?: string;
  occurred_at?: number;
  queue_item_id?: string | null;
  handoff_id?: string | null;
  permission_request_id?: string | null;
}

interface TimelineData {
  events: TimelineEvent[];
  total: number;
  closure_id?: string | null;
  message_cn?: string;
}

interface Props {
  baseUrl: string;
  closureId?: string | null;
  api: {
    fetchAuditTimeline: (baseUrl: string, closureId?: string) => Promise<Record<string, unknown>>;
  };
}

const SOURCE_CN: Record<string, string> = {
  queue: '执行队列', handoff: '人工交接', closure: '任务闭环', permission: '权限审批',
};

function mapEvents(raw: Record<string, unknown>): TimelineData {
  return {
    events: Array.isArray(raw.events) ? (raw.events as Record<string, unknown>[]).map((e: Record<string, unknown>) => ({
      id: (e.id as string) || '',
      source: (e.source as string) || '',
      status: (e.status as string) || '',
      label: (e.label as string) || '',
      summary: (e.summary as string) || '',
      occurred_at: (e.occurred_at as number) || 0,
    })) : [],
    total: (raw.total as number) || 0,
    closure_id: (raw.closure_id as string) || null,
    message_cn: (raw.message_cn as string) || undefined,
  };
}

export function AuditTimelinePanel({ baseUrl, closureId, api }: Props) {
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const raw = await api.fetchAuditTimeline(baseUrl, closureId || undefined);
        if (cancelled) return;
        setData(mapEvents(raw));
      } catch (e) {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [baseUrl, closureId]);

  if (loading) return <div className="auditTimelinePanel" style={{ padding: '1rem', color: '#888' }}>加载中…</div>;
  if (error) return <div className="auditTimelinePanel" style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  if (!data) return <div className="auditTimelinePanel" style={{ padding: '1rem', color: '#888' }}>暂无数据。</div>;
  if (data.message_cn) return <div className="auditTimelinePanel" style={{ padding: '1rem', color: '#888' }}>{data.message_cn}</div>;

  return (
    <div className="auditTimelinePanel" style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>审计时间线</h2>
      <div style={{ fontSize: '0.75rem', color: '#888', marginBottom: '0.5rem' }}>
        {data.total} 条事件{data.closure_id ? `（闭环：${data.closure_id}）` : '（最近）'}
      </div>
      {data.events.length === 0 ? (
        <div style={{ color: '#888', padding: '1rem' }}>暂无审计事件。</div>
      ) : (
        <div style={{ maxHeight: '35vh', overflowY: 'auto' }}>
          {data.events.map((ev, i) => (
            <div key={ev.id || i} style={{
              padding: '4px 8px', margin: '2px 0', borderRadius: '3px',
              borderLeft: `3px solid ${ev.status === 'blocked' || ev.status === 'failed' ? '#d44' : ev.status === 'completed' ? '#4a4' : '#aaa'}`,
              background: '#fafafa', fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>
                  <span style={{ fontSize: '0.7rem', color: '#666', marginRight: '6px' }}>
                    [{SOURCE_CN[ev.source || ''] || ev.source || '未知'}]
                  </span>
                  {ev.label || ev.summary}
                </span>
                {ev.occurred_at ? (
                  <span style={{ fontSize: '0.65rem', color: '#999' }}>
                    {new Date(ev.occurred_at * 1000).toLocaleString('zh-CN')}
                  </span>
                ) : null}
              </div>
              {ev.summary && ev.label && ev.label !== ev.summary && (
                <div style={{ fontSize: '0.7rem', color: '#888', marginTop: '2px' }}>{ev.summary}</div>
              )}
            </div>
          ))}
        </div>
      )}
      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板为只读审计视图，可追溯 queue→handoff→permission→closure→evidence 全过程，不提供执行按钮。
      </div>
    </div>
  );
}
