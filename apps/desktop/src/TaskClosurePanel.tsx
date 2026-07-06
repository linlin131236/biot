import { useState, useCallback } from 'react';
import { TASK_TEMPLATES, TASK_CLOSURE_LABELS, type TaskClosureEvidence, type TaskClosureStatus, type TaskTemplate, type TaskTemplateId } from '@bolt/shared/autonomy';
import { fetchTaskTemplates, createTaskClosure, getTaskClosure, addClosureEvent, addClosureReview, bindTaskClosureRun, bindTaskClosureGoal } from './harnessClientAutonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

type CreateTaskClosurePayload = { objective: string; template_id: TaskTemplateId; run_id?: string; goal_id?: string };
type ClosureEventPayload = { type: 'command'; command: string; result: string };

export interface TaskClosurePanelApi {
  fetchTaskTemplates: (b: string, f?: Fetcher) => Promise<TaskTemplate[]>;
  createTaskClosure: (b: string, p: CreateTaskClosurePayload, f?: Fetcher) => Promise<TaskClosureEvidence>;
  getTaskClosure: (b: string, id: string, f?: Fetcher) => Promise<TaskClosureEvidence>;
  addClosureEvent: (b: string, id: string, p: ClosureEventPayload, f?: Fetcher) => Promise<TaskClosureEvidence>;
  addClosureReview: (b: string, id: string, p: { summary: string; passed: boolean }, f?: Fetcher) => Promise<TaskClosureEvidence>;
  bindTaskClosureRun: (b: string, id: string, runId: string, f?: Fetcher) => Promise<TaskClosureEvidence>;
  bindTaskClosureGoal: (b: string, id: string, goalId: string, f?: Fetcher) => Promise<TaskClosureEvidence>;
}

export interface TaskClosurePanelProps {
  baseUrl: string;
  workspace: string;
  fetcher?: Fetcher;
  runId?: string | null;
  goalId?: string | null;
  api?: TaskClosurePanelApi;
}

function errorMessage(value: unknown, fallback: string): string {
  return value instanceof Error ? value.message : fallback;
}

function closureStatus(closure: TaskClosureEvidence): TaskClosureStatus {
  return closure.final_status ?? closure.status ?? 'pending';
}

function statusHint(status: TaskClosureStatus): string | null {
  if (status === 'waiting_permission') return '等待人工批准';
  if (status === 'stopped') return '已达到最大步数';
  if (status === 'failed') return '需要人工处理';
  if (status === 'executing' || status === 'repairing') return '自动记录中';
  return null;
}

export default function TaskClosurePanel({ baseUrl, workspace, fetcher, runId, goalId, api }: TaskClosurePanelProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<TaskTemplateId>('bugfix');
  const [objective, setObjective] = useState('');
  const [closure, setClosure] = useState<TaskClosureEvidence | null>(null);
  const [error, setError] = useState('');
  const [cmdText, setCmdText] = useState('');
  const [cmdResult, setCmdResult] = useState('');
  const [reviewSummary, setReviewSummary] = useState('');
  const [reviewPassed, setReviewPassed] = useState(false);
  const disabled = !workspace;
  const call = api ?? { fetchTaskTemplates, createTaskClosure, getTaskClosure, addClosureEvent, addClosureReview, bindTaskClosureRun, bindTaskClosureGoal };

  const handleCreate = useCallback(async () => {
    if (!objective.trim()) { setError('请输入任务目标'); return; }
    try {
      const data = await call.createTaskClosure(baseUrl, { objective, template_id: selectedTemplate, run_id: runId ?? undefined, goal_id: goalId ?? undefined }, fetcher);
      setClosure(data);
      setError('');
    } catch (e) { setError(errorMessage(e, '创建失败')); }
  }, [objective, selectedTemplate, baseUrl, fetcher, runId, goalId, call]);

  const handleRefresh = useCallback(async () => {
    if (!closure) return;
    try { setClosure(await call.getTaskClosure(baseUrl, closure.id, fetcher)); } catch (e) { setError(errorMessage(e, '刷新失败')); }
  }, [closure, baseUrl, fetcher, call]);

  const handleBindRun = useCallback(async () => {
    if (!closure || !runId) return;
    try { setClosure(await call.bindTaskClosureRun(baseUrl, closure.id, runId, fetcher)); } catch (e) { setError(errorMessage(e, '绑定失败')); }
  }, [closure, runId, baseUrl, fetcher, call]);

  const handleBindGoal = useCallback(async () => {
    if (!closure || !goalId) return;
    try { setClosure(await call.bindTaskClosureGoal(baseUrl, closure.id, goalId, fetcher)); } catch (e) { setError(errorMessage(e, '绑定失败')); }
  }, [closure, goalId, baseUrl, fetcher, call]);

  const handleRecordCommand = useCallback(async () => {
    if (!closure || !cmdText.trim()) return;
    try {
      setClosure(await call.addClosureEvent(baseUrl, closure.id, { type: 'command', command: cmdText, result: cmdResult }, fetcher));
      setCmdText('');
      setCmdResult('');
    } catch (e) { setError(errorMessage(e, '记录失败')); }
  }, [closure, cmdText, cmdResult, baseUrl, fetcher, call]);

  const handleRecordReview = useCallback(async () => {
    if (!closure) return;
    try {
      setClosure(await call.addClosureReview(baseUrl, closure.id, { summary: reviewSummary, passed: reviewPassed }, fetcher));
      setReviewSummary('');
    } catch (e) { setError(errorMessage(e, '记录失败')); }
  }, [closure, reviewSummary, reviewPassed, baseUrl, fetcher, call]);

  const currentStatus = closure ? closureStatus(closure) : null;
  const hint = currentStatus ? statusHint(currentStatus) : null;

  return (
    <div style={{ padding: '0.75rem', border: '1px solid #333', borderRadius: '0.25rem' }}>
      <h3 style={{ margin: '0 0 0.5rem' }}>任务闭环</h3>
      {!closure && <CreateClosureForm disabled={disabled} selectedTemplate={selectedTemplate} objective={objective} setSelectedTemplate={setSelectedTemplate} setObjective={setObjective} handleCreate={handleCreate} />}
      {closure && <>
        <div>当前闭环：{closure.id}</div>
        <div>目标：{closure.objective}</div>
        <div>当前状态：{TASK_CLOSURE_LABELS[currentStatus ?? 'pending']}</div>
        {hint ? <div>{hint}</div> : null}
        <div>已绑定运行：{closure.run_id || '未绑定'}</div>
        <div>已绑定目标：{closure.goal_id || '未绑定'}</div>
        <div style={{ marginTop: '0.25rem' }}>
          {runId ? <button type="button" onClick={handleBindRun} disabled={disabled}>绑定当前运行</button> : null}
          {goalId ? <button type="button" onClick={handleBindGoal} disabled={disabled}>绑定当前目标</button> : null}
        </div>
        {closure.changed_files.length > 0 && <div>变更文件：{closure.changed_files.join(', ')}</div>}
        {closure.commands.length > 0 && <div>验证命令：{closure.commands.join(', ')}</div>}
        {closure.command_results.length > 0 && <div>验证结果：{closure.command_results.join(', ')}</div>}
        {closure.retry_count > 0 && <div>修复次数：{closure.retry_count}</div>}
        {closure.review_summary && <div>审查摘要：{closure.review_summary}</div>}
        {closure.next_action && <div>下一步建议：{closure.next_action}</div>}
        <hr style={{ borderColor: '#444' }} />
        <input value={cmdText} onChange={e => setCmdText(e.target.value)} placeholder="验证命令" style={{ width: '8rem', marginRight: '0.25rem' }} />
        <input value={cmdResult} onChange={e => setCmdResult(e.target.value)} placeholder="验证结果" style={{ width: '8rem', marginRight: '0.25rem' }} />
        <button type="button" onClick={handleRecordCommand}>记录验证结果</button>
        <div style={{ marginTop: '0.25rem' }}>
          <input value={reviewSummary} onChange={e => setReviewSummary(e.target.value)} placeholder="审查摘要" style={{ width: '12rem', marginRight: '0.25rem' }} />
          <label><input type="checkbox" checked={reviewPassed} onChange={e => setReviewPassed(e.target.checked)} />通过</label>
          <button type="button" onClick={handleRecordReview}>记录审查摘要</button>
        </div>
        <button type="button" onClick={handleRefresh} style={{ marginTop: '0.25rem' }}>刷新闭环状态</button>
      </>}
      {error && <div style={{ color: '#f66', marginTop: '0.25rem' }}>{error}</div>}
      {disabled && <div style={{ color: '#888', marginTop: '0.25rem' }}>请先选择工作区</div>}
    </div>
  );
}

function CreateClosureForm(props: { disabled: boolean; selectedTemplate: TaskTemplateId; objective: string; setSelectedTemplate: (v: TaskTemplateId) => void; setObjective: (v: string) => void; handleCreate: () => void }) {
  return <>
    <select value={props.selectedTemplate} onChange={e => props.setSelectedTemplate(e.target.value as TaskTemplateId)} disabled={props.disabled} style={{ marginRight: '0.5rem' }}>
      {TASK_TEMPLATES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
    </select>
    <input value={props.objective} onChange={e => props.setObjective(e.target.value)} placeholder="输入任务目标" disabled={props.disabled} style={{ width: '12rem', marginRight: '0.5rem' }} />
    <button type="button" onClick={props.handleCreate} disabled={props.disabled}>创建闭环任务</button>
  </>;
}
