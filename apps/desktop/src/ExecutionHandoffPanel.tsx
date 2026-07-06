import { useCallback, useEffect, useState } from 'react';
import type { ExecutionAuditTimelineEvent, ExecutionHandoffRecord } from '@bolt/shared/autonomy';
import { completeExecutionHandoff, createExecutionHandoff, failExecutionHandoff, fetchExecutionAuditTimeline, fetchExecutionHandoffs, requestExecutionHandoffPermission } from './harnessClientAutonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface ExecutionHandoffPanelApi {
  fetchExecutionHandoffs: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionHandoffRecord[]>;
  fetchExecutionAuditTimeline: (b: string, closureId: string, f?: Fetcher) => Promise<ExecutionAuditTimelineEvent[]>;
  createExecutionHandoff: (b: string, itemId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  completeExecutionHandoff: (b: string, handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  failExecutionHandoff: (b: string, handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  requestExecutionHandoffPermission: (b: string, handoffId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
}

interface Props { baseUrl: string; closureId?: string | null; selectedQueueItemId?: string | null; fetcher?: Fetcher; api?: ExecutionHandoffPanelApi; }

const defaultApi = { fetchExecutionHandoffs, fetchExecutionAuditTimeline, createExecutionHandoff, completeExecutionHandoff, failExecutionHandoff, requestExecutionHandoffPermission };
const terminal = new Set(['completed', 'failed']);

export default function ExecutionHandoffPanel({ baseUrl, closureId, selectedQueueItemId, fetcher, api }: Props) {
  const [records, setRecords] = useState<ExecutionHandoffRecord[]>([]);
  const [timeline, setTimeline] = useState<ExecutionAuditTimelineEvent[]>([]);
  const [error, setError] = useState('');
  const call = api ?? defaultApi;
  const refresh = useCallback(async () => {
    if (!closureId) return;
    const [nextRecords, nextTimeline] = await Promise.all([
      call.fetchExecutionHandoffs(baseUrl, closureId, fetcher),
      call.fetchExecutionAuditTimeline(baseUrl, closureId, fetcher),
    ]);
    setRecords(nextRecords);
    setTimeline(nextTimeline);
  }, [baseUrl, closureId, fetcher, call]);

  useEffect(() => { refresh().catch(() => setError('加载失败')); }, [refresh]);

  async function createHandoff() {
    if (!selectedQueueItemId) { setError('请先选择已批准队列项'); return; }
    try {
      const next = await call.createExecutionHandoff(baseUrl, selectedQueueItemId, fetcher);
      if (next.closure_id !== closureId) { setError('交接记录不属于当前闭环任务'); return; }
      setRecords(current => current.some(record => record.id === next.id) ? current : [...current, next]);
      setError('');
    } catch { setError('生成失败'); }
  }

  async function update(action: () => Promise<ExecutionHandoffRecord>) {
    try {
      const next = await action();
      setRecords(current => current.map(record => record.id === next.id ? next : record));
    } catch { setError('操作失败'); }
  }

  if (!closureId) return <aside className="panel"><h2>安全交接</h2><p>暂无闭环任务</p></aside>;
  return <aside className="panel"><h2>安全交接</h2><button type="button" onClick={createHandoff}>生成安全交接</button>{records.length ? records.map(record => <HandoffItem key={record.id} record={record} update={update} api={call} baseUrl={baseUrl} fetcher={fetcher} />) : <p>需要人工处理</p>}<Timeline events={timeline} />{error ? <p>{error}</p> : null}</aside>;
}

function HandoffItem({ record, update, api, baseUrl, fetcher }: { record: ExecutionHandoffRecord; update: (a: () => Promise<ExecutionHandoffRecord>) => void; api: ExecutionHandoffPanelApi; baseUrl: string; fetcher?: Fetcher }) {
  const [note, setNote] = useState('');
  const active = !terminal.has(record.status);
  return <div className="stack"><strong>{record.title}</strong><span>{instruction(record)}</span>{record.command ? <code>{record.command}</code> : null}{record.permission_status === 'pending_permission' ? <span>等待人工执行权限</span> : null}{record.bridge_error ? <span>申请失败：{record.bridge_error}</span> : null}{record.goal_objective ? <span>建议目标：{record.goal_objective}</span> : null}{record.handoff_type === 'manual_verification' && record.status === 'ready_for_manual_action' ? <button type="button" onClick={() => update(() => api.requestExecutionHandoffPermission(baseUrl, record.id, fetcher))}>申请人工执行权限</button> : null}{record.handoff_type === 'goal_input' && active ? <button type="button" onClick={() => setNote('已复制为目标草稿')}>复制为目标草稿</button> : null}{record.handoff_type === 'goal_input' && active ? <button type="button" onClick={() => setNote('已记录为待创建目标')}>记录为待创建目标</button> : null}{note ? <span>{note}</span> : null}{active ? <div className="actions"><button type="button" onClick={() => update(() => api.completeExecutionHandoff(baseUrl, record.id, '用户已完成', fetcher))}>标记完成</button><button type="button" onClick={() => update(() => api.failExecutionHandoff(baseUrl, record.id, '用户标记失败', fetcher))}>标记失败</button></div> : null}</div>;
}

function Timeline({ events }: { events: ExecutionAuditTimelineEvent[] }) {
  return <section className="stack"><h3>执行审计时间线</h3>{events.length ? events.map(event => <div key={event.id}><strong>{event.label}</strong><span>{event.summary}</span></div>) : <p>暂无审计记录</p>}</section>;
}

function instruction(record: ExecutionHandoffRecord): string {
  if (record.handoff_type === 'manual_verification') return '请在外部终端人工运行';
  if (record.handoff_type === 'permission_panel') return '请到权限面板处理原始权限请求';
  if (record.handoff_type === 'goal_input') return '建议目标文本';
  return record.instruction || '需要人工处理';
}
