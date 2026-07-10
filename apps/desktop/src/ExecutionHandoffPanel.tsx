import { useCallback, useEffect, useState } from 'react';
import type { ExecutionAuditDiagnostic, ExecutionAuditIntegrity, ExecutionAuditTimelineEvent, ExecutionHandoffRecord } from '@bolt/shared/autonomy';
import type { LocalReleaseChecklist, RecoveryPolicy, ReleaseReadiness, TaskGraphSummary } from '@bolt/shared/release';
import { completeExecutionHandoff, createExecutionHandoff, failExecutionHandoff, fetchExecutionAuditDiagnostics, fetchExecutionAuditIntegrity, fetchExecutionAuditTimeline, fetchExecutionHandoffs, fetchLocalReleaseChecklist, fetchPlannerGraphs, fetchRecoveryPolicy, fetchReleaseReadiness, requestExecutionHandoffPermission } from './harnessClientAutonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface ExecutionHandoffPanelApi {
  fetchExecutionHandoffs: (closureId?: string, f?: Fetcher) => Promise<ExecutionHandoffRecord[]>;
  fetchExecutionAuditTimeline: (closureId: string, f?: Fetcher) => Promise<ExecutionAuditTimelineEvent[]>;
  fetchExecutionAuditDiagnostics: (closureId?: string, f?: Fetcher) => Promise<ExecutionAuditDiagnostic[]>;
  fetchExecutionAuditIntegrity: (f?: Fetcher) => Promise<ExecutionAuditIntegrity[]>;
  fetchReleaseReadiness: (f?: Fetcher) => Promise<ReleaseReadiness>;
  fetchLocalReleaseChecklist: (f?: Fetcher) => Promise<LocalReleaseChecklist>;
  fetchRecoveryPolicy: (f?: Fetcher) => Promise<RecoveryPolicy>;
  fetchPlannerGraphs: (f?: Fetcher) => Promise<TaskGraphSummary[]>;
  createExecutionHandoff: (itemId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  completeExecutionHandoff: (handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  failExecutionHandoff: (handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
  requestExecutionHandoffPermission: (handoffId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>;
}

interface Props { closureId?: string | null; selectedQueueItemId?: string | null; fetcher?: Fetcher; api?: ExecutionHandoffPanelApi; }

const defaultApi = { fetchExecutionHandoffs, fetchExecutionAuditTimeline, fetchExecutionAuditDiagnostics, fetchExecutionAuditIntegrity, fetchReleaseReadiness, fetchLocalReleaseChecklist, fetchRecoveryPolicy, fetchPlannerGraphs, createExecutionHandoff, completeExecutionHandoff, failExecutionHandoff, requestExecutionHandoffPermission };
const terminal = new Set(['completed', 'failed']);

export default function ExecutionHandoffPanel({ closureId, selectedQueueItemId, fetcher, api }: Props) {
  const [records, setRecords] = useState<ExecutionHandoffRecord[]>([]);
  const [timeline, setTimeline] = useState<ExecutionAuditTimelineEvent[]>([]);
  const [diagnostics, setDiagnostics] = useState<ExecutionAuditDiagnostic[]>([]);
  const [integrity, setIntegrity] = useState<ExecutionAuditIntegrity[]>([]);
  const [readiness, setReadiness] = useState<ReleaseReadiness | null>(null);
  const [checklist, setChecklist] = useState<LocalReleaseChecklist | null>(null);
  const [recovery, setRecovery] = useState<RecoveryPolicy | null>(null);
  const [plannerGraphs, setPlannerGraphs] = useState<TaskGraphSummary[]>([]);
  const [error, setError] = useState('');
  const call = api ?? defaultApi;
  const refresh = useCallback(async () => {
    if (!closureId) return;
    const [nextRecords, nextTimeline, nextDiagnostics] = await Promise.all([
      call.fetchExecutionHandoffs(closureId, fetcher),
      call.fetchExecutionAuditTimeline(closureId, fetcher),
      call.fetchExecutionAuditDiagnostics(closureId, fetcher),
    ]);
    setRecords(nextRecords);
    setTimeline(nextTimeline);
    setDiagnostics(nextDiagnostics);
  }, [closureId, fetcher, call]);

  useEffect(() => { refresh().catch(() => setError('加载失败')); }, [refresh]);

  useEffect(() => {
    call.fetchExecutionAuditIntegrity(fetcher).then(data => setIntegrity(Array.isArray(data) ? data : [])).catch(() => { /* integrity fetch is best-effort */ });
  }, [fetcher, call]);

  useEffect(() => {
    call.fetchReleaseReadiness(fetcher).then(setReadiness).catch(() => { /* readiness fetch is best-effort */ });
  }, [fetcher, call]);

  useEffect(() => {
    call.fetchLocalReleaseChecklist(fetcher).then(setChecklist).catch(() => { /* checklist fetch is best-effort */ });
  }, [fetcher, call]);

  useEffect(() => {
    call.fetchRecoveryPolicy(fetcher).then(setRecovery).catch(() => { /* recovery policy fetch is best-effort */ });
  }, [fetcher, call]);

  useEffect(() => {
    call.fetchPlannerGraphs(fetcher).then(data => setPlannerGraphs(Array.isArray(data) ? data : [])).catch(() => { /* planner graphs fetch is best-effort */ });
  }, [fetcher, call]);

  async function createHandoff() {
    if (!selectedQueueItemId) { setError('请先选择已批准队列项'); return; }
    try {
      const next = await call.createExecutionHandoff(selectedQueueItemId, fetcher);
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
  return <aside className="panel"><h2>安全交接</h2><button type="button" onClick={createHandoff}>生成安全交接</button>{records.length ? records.map(record => <HandoffItem key={record.id} record={record} update={update} api={call} fetcher={fetcher} />) : <p>需要人工处理</p>}<Timeline events={timeline} /><Integrity items={integrity} /><Readiness data={readiness} /><Checklist data={checklist} /><RecoveryPanel data={recovery} /><PlannerGraphs graphs={plannerGraphs} /><Diagnostics items={diagnostics} />{error ? <p>{error}</p> : null}</aside>;
}

function HandoffItem({ record, update, api, fetcher }: { record: ExecutionHandoffRecord; update: (a: () => Promise<ExecutionHandoffRecord>) => void; api: ExecutionHandoffPanelApi; fetcher?: Fetcher }) {
  const [note, setNote] = useState('');
  const active = !terminal.has(record.status);
  return <div className="stack"><strong>{record.title}</strong><span>{instruction(record)}</span>{record.command ? <code>{record.command}</code> : null}{record.permission_status === 'pending_permission' ? <span>等待人工执行权限</span> : null}{record.bridge_error ? <span>申请失败：{record.bridge_error}</span> : null}{record.goal_objective ? <span>建议目标：{record.goal_objective}</span> : null}{record.handoff_type === 'manual_verification' && record.status === 'ready_for_manual_action' ? <button type="button" onClick={() => update(() => api.requestExecutionHandoffPermission(record.id, fetcher))}>申请人工执行权限</button> : null}{record.handoff_type === 'goal_input' && active ? <button type="button" onClick={() => setNote('已复制为目标草稿')}>复制为目标草稿</button> : null}{record.handoff_type === 'goal_input' && active ? <button type="button" onClick={() => setNote('已记录为待创建目标')}>记录为待创建目标</button> : null}{note ? <span>{note}</span> : null}{active ? <div className="actions"><button type="button" onClick={() => update(() => api.completeExecutionHandoff(record.id, '用户已完成', fetcher))}>标记完成</button><button type="button" onClick={() => update(() => api.failExecutionHandoff(record.id, '用户标记失败', fetcher))}>标记失败</button></div> : null}</div>;
}

function Timeline({ events }: { events: ExecutionAuditTimelineEvent[] }) {
  return <section className="stack"><h3>执行审计时间线</h3>{events.length ? events.map(event => <div key={event.id}><strong>{event.label}</strong><span>{event.summary}</span></div>) : <p>暂无审计记录</p>}</section>;
}

function Diagnostics({ items }: { items: ExecutionAuditDiagnostic[] }) {
  return <section className="stack"><h3>审计一致性诊断</h3>{items.length ? items.map(item => <div key={item.id}><strong>{item.severity_label}</strong><span>{item.summary}</span><span>{item.suggestion}</span></div>) : <p>暂无诊断问题</p>}</section>;
}

function Integrity({ items }: { items: ExecutionAuditIntegrity[] }) {
  const list = Array.isArray(items) ? items : [];
  const summary = list.length === 0 ? '审计文件正常'
    : list.some(item => item.severity === 'blocking') ? '审计文件损坏'
    : list.every(item => item.code === 'clean') ? '审计文件正常'
    : '需要人工处理';
  return <section className="stack"><h3>审计文件完整性</h3><p><strong>{summary}</strong></p>{list.map(item => <div key={item.id}><strong>{item.severity_label}</strong><span>{item.summary}</span><span>{item.suggestion}</span></div>)}</section>;
}

function Readiness({ data }: { data: ReleaseReadiness | null }) {
  if (!data) return <section className="stack"><h3>发布准备度</h3><p>加载中...</p></section>;
  return <section className="stack">
    <h3>发布准备度</h3>
    <p><strong>{data.ready ? '✅ 可以发布' : '❌ 存在阻断项'}</strong></p>
    {data.blockers.length > 0 && <div><strong>阻断项：</strong><ul>{data.blockers.map((b, i) => <li key={i}>{b}</li>)}</ul></div>}
    {data.warnings.length > 0 && <div><strong>警告项：</strong><ul>{data.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
    <div><strong>已通过检查：</strong><ul>{data.checks.filter(c => c.passed).map(c => <li key={c.code}>{c.label}：{c.detail}</li>)}</ul></div>
    {!data.ready && <p>建议下一步：人工审核后再由用户确认 push/release</p>}
  </section>;
}

function Checklist({ data }: { data: LocalReleaseChecklist | null }) {
  if (!data) return <section className="stack"><h3>本地发布检查清单</h3><p>加载中...</p></section>;
  return <section className="stack">
    <h3>本地发布检查清单</h3>
    <p><em>{data.disclaimer}</em></p>
    <p><strong>{data.ready ? '✅ 所有阻断项通过' : '❌ 存在阻断项'}</strong></p>
    {data.blockers.length > 0 && <div><strong>阻断项：</strong><ul>{data.blockers.map((b, i) => <li key={i}>{b}</li>)}</ul></div>}
    {data.warnings.length > 0 && <div><strong>警告项：</strong><ul>{data.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
    <table>
      <thead><tr><th>分类</th><th>检查项</th><th>状态</th><th>详情</th><th>建议</th></tr></thead>
      <tbody>
        {data.items.map(item => <tr key={item.code}>
          <td>{item.category}</td>
          <td>{item.label}</td>
          <td>{item.status_label}</td>
          <td>{item.detail}</td>
          <td>{item.recommendation || '—'}</td>
        </tr>)}
      </tbody>
    </table>
    <p><strong>下一步：</strong>{data.next_step}</p>
  </section>;
}

function RecoveryPanel({ data }: { data: RecoveryPolicy | null }) {
  if (!data) return <section className="stack"><h3>故障恢复策略</h3><p>加载中...</p></section>;
  return <section className="stack">
    <h3>故障恢复策略</h3>
    <p><em>{data.disclaimer}</em></p>
    {data.scenarios.map(s => <details key={s.code}>
      <summary><strong>{s.severity_label} {s.title}</strong> — {s.auto_recovery_label}</summary>
      <p>{s.description}</p>
      <div><strong>恢复步骤：</strong><ol>{s.recovery_steps.map((step, i) => <li key={i}>{step}</li>)}</ol></div>
      {s.warnings.length > 0 && <div><strong>⚠️ 警告：</strong><ul>{s.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></div>}
    </details>)}
  </section>;
}

function PlannerGraphs({ graphs }: { graphs: TaskGraphSummary[] }) {
  const statusLabels: Record<string, string> = {
    pending: '待处理', in_progress: '进行中', blocked: '已阻塞', completed: '已完成', failed: '已失败',
  };
  return <section className="stack">
    <h3>任务规划图</h3>
    <p><em>仅规划，不自动执行。任务执行需通过任务闭环 + 执行队列 + PermissionGate 流程。</em></p>
    {graphs.length === 0 ? <p>暂无任务规划图</p> : graphs.map(g => <div key={g.id}>
      <strong>{g.title}</strong>
      <span>{g.objective}</span>
      <span>节点数：{g.node_count}</span>
    </div>)}
  </section>;
}

function instruction(record: ExecutionHandoffRecord): string {
  if (record.handoff_type === 'manual_verification') return '请在外部终端人工运行';
  if (record.handoff_type === 'permission_panel') return '请到权限面板处理原始权限请求';
  if (record.handoff_type === 'goal_input') return '建议目标文本';
  return record.instruction || '需要人工处理';
}
