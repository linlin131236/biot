import { useCallback, useEffect, useState } from 'react';
import type { ExecutionQueueItem } from '@bolt/shared/autonomy';
import { approveExecutionQueueItem, completeExecutionQueueItem, failExecutionQueueItem, fetchExecutionQueue, proposeExecutionQueue, rejectExecutionQueueItem } from './harnessClientAutonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface ExecutionQueuePanelApi {
  fetchExecutionQueue: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>;
  proposeExecutionQueue: (b: string, closureId: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>;
  approveExecutionQueueItem: (b: string, itemId: string, f?: Fetcher) => Promise<ExecutionQueueItem>;
  rejectExecutionQueueItem: (b: string, itemId: string, reason: string, f?: Fetcher) => Promise<ExecutionQueueItem>;
  completeExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem>;
  failExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem>;
}

interface Props { baseUrl: string; closureId?: string | null; fetcher?: Fetcher; api?: ExecutionQueuePanelApi; }

const defaultApi = { fetchExecutionQueue, proposeExecutionQueue, approveExecutionQueueItem, rejectExecutionQueueItem, completeExecutionQueueItem, failExecutionQueueItem };
const riskLabels: Record<string, string> = { read_only: '只读', verification_command: '验证命令', workspace_write: '工作区写入', destructive: '高风险' };
const statusLabels: Record<string, string> = { pending: '待批准', approved: '已批准', rejected: '已拒绝', completed: '已完成', failed: '已失败' };

export default function ExecutionQueuePanel({ baseUrl, closureId, fetcher, api }: Props) {
  const [items, setItems] = useState<ExecutionQueueItem[]>([]);
  const [error, setError] = useState('');
  const call = api ?? defaultApi;
  const refresh = useCallback(async () => {
    if (!closureId) return;
    setItems(await call.fetchExecutionQueue(baseUrl, closureId, fetcher));
  }, [baseUrl, closureId, fetcher, call]);

  useEffect(() => { refresh().catch(() => setError('加载失败')); }, [refresh]);

  async function propose() {
    if (!closureId) return;
    try { await call.proposeExecutionQueue(baseUrl, closureId, fetcher); await refresh(); } catch { setError('生成失败'); }
  }

  async function update(action: () => Promise<ExecutionQueueItem>) {
    try {
      const next = await action();
      setItems(current => current.map(item => item.id === next.id ? next : item));
    } catch { setError('操作失败'); }
  }

  if (!closureId) return <aside className="panel"><h2>安全执行队列</h2><p>暂无闭环任务</p></aside>;
  return <aside className="panel"><h2>安全执行队列</h2><button type="button" onClick={propose}>生成待处理动作</button><h3>待处理动作</h3>{items.length ? items.map(item => <QueueItem key={item.id} item={item} update={update} api={call} baseUrl={baseUrl} fetcher={fetcher} />) : <p>需要人工处理</p>}{error ? <p>{error}</p> : null}</aside>;
}

function QueueItem({ item, update, api, baseUrl, fetcher }: { item: ExecutionQueueItem; update: (a: () => Promise<ExecutionQueueItem>) => void; api: ExecutionQueuePanelApi; baseUrl: string; fetcher?: Fetcher }) {
  const canCompletePending = item.status === 'pending' && (item.risk === 'read_only' || item.kind === 'manual_review');
  return <div className="stack"><strong>{item.title}</strong><span>{item.description}</span><span>风险等级：{riskLabels[item.risk]}</span><span>{statusLabels[item.status]}</span>{item.command ? <code>命令建议：{item.command}（不执行命令）</code> : null}<div className="actions">{item.status === 'pending' ? <><button type="button" onClick={() => update(() => api.approveExecutionQueueItem(baseUrl, item.id, fetcher))}>批准</button><button type="button" onClick={() => update(() => api.rejectExecutionQueueItem(baseUrl, item.id, '用户拒绝', fetcher))}>拒绝</button></> : null}{canCompletePending || item.status === 'approved' ? <button type="button" onClick={() => update(() => api.completeExecutionQueueItem(baseUrl, item.id, '用户已完成', fetcher))}>标记完成</button> : null}{item.status === 'approved' ? <button type="button" onClick={() => update(() => api.failExecutionQueueItem(baseUrl, item.id, '用户标记失败', fetcher))}>标记失败</button> : null}</div></div>;
}
