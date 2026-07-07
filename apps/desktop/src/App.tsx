import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { AlertTriangle, CheckCircle2, FolderOpen, RefreshCw, ShieldCheck } from 'lucide-react';
import type { MemorySnapshot, ModelSettings, PendingPermission, ToolResult } from '@bolt/shared';
import type { Goal } from '@bolt/shared/autonomy';
import { fetchHarnessTrace, fetchMemorySnapshot, fetchPendingPermissions, submitToolRequest } from './harnessClient';
import { createBoltState, reduceBoltState, type BoltState } from './state';
import { loadDesktopSession, saveDesktopSession, type DesktopSession } from './desktopSession';
import { fetchCoreHealth } from './coreClient';
import { decidePermission, evaluateWorkflowReview, executeWorkflowStep, loadModelSettings, maintainMemory, refreshWorkflow, startWorkflowRun, storeModelSettings, createWorkflowGoal, fetchWorkflowTimeline } from './workflowClient';
import { PanelsSection } from './PanelsSection';
import { fetchUnfinishedGoals } from './harnessClientAutonomy';
import { createPanelsApi } from './panelsApi';
import './styles.css';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

async function defaultSelectWorkspace(): Promise<string | null> {
  if (typeof window !== 'undefined' && window.bolt?.selectWorkspace) {
    return window.bolt.selectWorkspace();
  }
  const path = prompt('请输入工作区路径：');
  return path || null;
}

interface AppProps {
  fetcher?: Fetcher;
  initialMemorySnapshot?: MemorySnapshot;
  initialPendingPermissions?: PendingPermission[];
  selectWorkspace?: () => Promise<string | null>;
}

export function App({ fetcher = fetch, initialMemorySnapshot, initialPendingPermissions = [], selectWorkspace = defaultSelectWorkspace }: AppProps) {
  const [session, setSession] = useState<DesktopSession>(() => loadDesktopSession());
  const [goal, setGoal] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<ModelSettings>({ provider: 'openai-compatible', base_url: 'http://localhost:11434/v1', model: 'fake-model', temperature: 0.2 });
  const [apiKey, setApiKey] = useState('');
  const [state, dispatch] = useReducer(reduceBoltState, createInitialState(session, initialMemorySnapshot, initialPendingPermissions));
  const [goalInfo, setGoalInfo] = useState<Goal | null>(null);
  const [reviewResult, setReviewResult] = useState<{ passed: boolean; failures: string[] } | null>(null);
  const [timeline, setTimeline] = useState<unknown[]>([]);
  const [unfinishedGoals, setUnfinishedGoals] = useState<Goal[]>([]);
  const [filePath, setFilePath] = useState('');
  const [oldText, setOldText] = useState('');
  const [newText, setNewText] = useState('');
  const runId = state.currentRunId || session.lastRunId;
  const panelsApi = useMemo(() => createPanelsApi(fetcher, goalInfo), [fetcher, goalInfo]);

  useEffect(() => {
    if (!session.completed) return;
    let active = true;
    fetchCoreHealth(session.coreUrl, fetcher).then((status) => { if (active) dispatch({ type: 'core.health.changed', status }); });
    fetchUnfinishedGoals(session.coreUrl, fetcher).then((goals) => { if (active) setUnfinishedGoals(goals); }).catch(() => {});
    return () => { active = false; };
  }, [fetcher, session.completed, session.coreUrl]);

  function completeFirstRun(next: DesktopSession) { saveSession(next); dispatch({ type: 'workspace.selected', path: next.workspacePath }); }

  async function guarded(action: () => Promise<void>, fallback: string) {
    try { setError(null); await action(); } catch (err) { setError(err instanceof Error && err.message.startsWith('Agent Core request failed') ? err.message : fallback); }
  }

  async function startRun() {
    await guarded(async () => { const run = await startWorkflowRun(session.coreUrl, goal || '继续任务', session.workspacePath, fetcher); dispatch({ type: 'harness.run.created', runId: run.id }); saveSession({ ...session, lastRunId: run.id }); }, '无法创建任务。');
  }

  async function createGoal() {
    await guarded(async () => { const g = await createWorkflowGoal(session.coreUrl, { objective: goal || 'Bolt 任务', criteria: ['文件读取', '补丁批准'], max_steps: 10, max_cost: 5.0, max_wall_time: 300, workspace: session.workspacePath }, fetcher); setGoalInfo(g); }, '无法创建目标。');
  }

  async function runStep() {
    if (!runId) return;
    await guarded(async () => { const { step, refresh } = await executeWorkflowStep(session.coreUrl, runId, fetcher); dispatch({ type: 'agent.step.recorded', result: step }); if (step.tool_result) dispatch({ type: 'tool.result.recorded', result: step.tool_result }); applyRefresh(refresh); }, '无法执行步骤。');
  }

  async function refreshTraceOnly() { if (!runId) return; await guarded(async () => dispatch({ type: 'harness.trace.loaded', events: await fetchHarnessTrace(session.coreUrl, runId, fetcher) }), '无法刷新轨迹。'); }
  async function refreshMemory() { await guarded(async () => dispatch({ type: 'memory.snapshot.loaded', snapshot: await fetchMemorySnapshot(session.coreUrl, fetcher) }), '无法连接 Agent Core。请确认服务已启动并检查核心服务地址。'); }
  async function refreshPermissions() { await guarded(async () => dispatch({ type: 'permissions.pending.loaded', permissions: await fetchPendingPermissions(session.coreUrl, fetcher) }), '无法加载权限请求。'); }

  async function onPermission(requestId: string, approved: boolean) {
    await guarded(async () => { const result = await decidePermission(session.coreUrl, requestId, approved, fetcher); dispatch({ type: 'tool.result.recorded', result }); if (runId) applyRefresh(await refreshWorkflow(session.coreUrl, runId, fetcher)); }, '无法处理权限请求。');
  }

  async function saveModel() { await guarded(async () => { const status = await storeModelSettings(session.coreUrl, { ...model, api_key: apiKey || undefined }, fetcher); dispatch({ type: 'model.settings.loaded', status }); setApiKey(''); }, '无法保存模型设置。'); }
  async function runGardener() { if (!runId) return; await guarded(async () => recordToolResult(await maintainMemory(session.coreUrl, runId, fetcher)), '无法运行文档整理。'); }
  async function fetchTimelineAction() { if (!runId) return; await guarded(async () => setTimeline(await fetchWorkflowTimeline(session.coreUrl, runId, fetcher)), '无法加载时间线。'); }
  const handleGoalConsoleChange = useCallback((g: Goal | null, rId: string | null) => {
    if (g && (g.id !== goalInfo?.id || g.status !== goalInfo?.status)) setGoalInfo(g);
    if (rId && rId !== (state.currentRunId || session.lastRunId)) { dispatch({ type: 'harness.run.created', runId: rId }); }
    if (rId && rId !== session.lastRunId) { saveSession({ ...session, lastRunId: rId }); }
  }, [goalInfo?.id, state.currentRunId, session.lastRunId, session]);

  async function runReview() { await guarded(async () => { const result = await evaluateWorkflowReview(session.coreUrl, { items: ['pytest', 'build'], results: { pytest: true, build: true } }, fetcher); setReviewResult(result); }, '无法评估审查。'); }

  async function readFile() {
    if (!hasWorkspace || !filePath || !runId) return;
    await guarded(async () => {
      const result = await submitToolRequest(session.coreUrl, runId, { tool: 'file.read', operation: 'read', payload: { path: filePath } }, fetcher);
      dispatch({ type: 'tool.result.recorded', result });
    }, '无法读取文件。');
  }

  async function submitPatch() {
    if (!hasWorkspace || !filePath || !oldText || !newText || !runId) return;
    await guarded(async () => {
      const result = await submitToolRequest(session.coreUrl, runId, { tool: 'file.patch', operation: 'patch', payload: { path: filePath, old_string: oldText, new_string: newText } }, fetcher);
      dispatch({ type: 'tool.result.recorded', result });
    }, '无法提交补丁。');
  }

  function applyRefresh(refresh: { trace?: BoltState['traceEvents']; memory?: MemorySnapshot; permissions?: PendingPermission[] }) {
    if (refresh.trace) dispatch({ type: 'harness.trace.loaded', events: refresh.trace });
    if (refresh.memory) dispatch({ type: 'memory.snapshot.loaded', snapshot: refresh.memory });
    if (refresh.permissions) dispatch({ type: 'permissions.pending.loaded', permissions: refresh.permissions });
  }

  function recordToolResult(result: ToolResult) { dispatch({ type: 'tool.result.recorded', result }); }
  function saveSession(next: DesktopSession) { saveDesktopSession(next); setSession(next); }

  async function changeWorkspace() {
    const path = await selectWorkspace();
    if (path) { const next = { ...session, workspacePath: path }; saveSession(next); dispatch({ type: 'workspace.selected', path }); }
  }

  const hasWorkspace = !!(state.workspacePath || session.workspacePath);

  if (!session.completed) return <FirstRunWizard session={session} onComplete={completeFirstRun} />;

  return <main className="shell"><aside className="sidebar"><div className="brand"><ShieldCheck size={22} /><h1>Bolt</h1></div><StatusRow label="Agent Core 状态" value={state.coreStatus} /><div className="statusRow"><span>工作区</span><strong>{hasWorkspace ? (state.workspacePath || session.workspacePath) : '工作区未选择'}</strong></div><button type="button" className="link" onClick={changeWorkspace}>{hasWorkspace ? '更换工作区' : '选择工作区'}</button><StatusRow label="核心服务地址" value={session.coreUrl} /><StatusRow label="当前运行" value={runId || '无'} /></aside><section className="workbench"><Toolbar goal={goal} setGoal={setGoal} runId={runId} hasWorkspace={hasWorkspace} startRun={startRun} createGoal={createGoal} runStep={runStep} refreshTrace={refreshTraceOnly} refreshMemory={refreshMemory} refreshPermissions={refreshPermissions} runGardener={runGardener} fetchTimeline={fetchTimelineAction} runReview={runReview} />{error ? <div className="error"><AlertTriangle size={16} />{error}</div> : null}<ToolFlowPanel hasWorkspace={hasWorkspace} filePath={filePath} setFilePath={setFilePath} oldText={oldText} setOldText={setOldText} newText={newText} setNewText={setNewText} readFile={readFile} submitPatch={submitPatch} /><ModelPanel model={model} setModel={setModel} apiKey={apiKey} setApiKey={setApiKey} saveModel={saveModel} status={state.modelSettingsStatus} /><section className="panels"><PanelsSection runId={runId} goalInfo={goalInfo} unfinishedGoals={unfinishedGoals} workspace={hasWorkspace ? (state.workspacePath || session.workspacePath) : ''} baseUrl={session.coreUrl} fetcher={fetcher} onGoalChange={handleGoalConsoleChange} api={panelsApi} /><TaskLog state={state} /><TracePanel state={state} /><DogfoodPanel goalInfo={goalInfo} reviewResult={reviewResult} timeline={timeline} /><PermissionsPanel permissions={state.pendingPermissions} onDecision={onPermission} /><MemoryPanel snapshot={state.memorySnapshot} /></section></section></main>;
}

function Toolbar(props: { goal: string; setGoal: (v: string) => void; runId: string | null; hasWorkspace: boolean; startRun: () => void; createGoal: () => void; runStep: () => void; refreshTrace: () => void; refreshMemory: () => void; refreshPermissions: () => void; runGardener: () => void; fetchTimeline: () => void; runReview: () => void }) {
  return <header className="toolbar"><label>任务目标<input aria-label="任务目标" value={props.goal} onChange={(e) => props.setGoal(e.target.value)} /></label><div className="actions"><button type="button" disabled={!props.hasWorkspace} onClick={props.startRun}>开始任务</button><button type="button" disabled={!props.hasWorkspace} onClick={props.createGoal}>创建目标</button><button type="button" disabled={!props.runId} onClick={props.runStep}>执行一步</button><button type="button" disabled={!props.runId} onClick={props.refreshTrace}>刷新轨迹</button><button type="button" onClick={props.refreshMemory}><RefreshCw size={16} />刷新记忆</button><button type="button" onClick={props.refreshPermissions}>刷新权限</button><button type="button" disabled={!props.runId} onClick={props.runGardener}>整理文档</button><button type="button" disabled={!props.runId} onClick={props.fetchTimeline}>时间线</button><button type="button" onClick={props.runReview}>审查</button></div></header>;
}

function ToolFlowPanel(props: { hasWorkspace: boolean; filePath: string; setFilePath: (v: string) => void; oldText: string; setOldText: (v: string) => void; newText: string; setNewText: (v: string) => void; readFile: () => void; submitPatch: () => void }) {
  return <section className="toolPanel"><label>文件路径<input aria-label="文件路径" placeholder="可输入相对路径，如 README.md" value={props.filePath} onChange={(e) => props.setFilePath(e.target.value)} /></label><label>原文本<input aria-label="原文本" value={props.oldText} onChange={(e) => props.setOldText(e.target.value)} /></label><label>新文本<input aria-label="新文本" value={props.newText} onChange={(e) => props.setNewText(e.target.value)} /></label><button type="button" disabled={!props.hasWorkspace} onClick={props.readFile}>读取文件</button><button type="button" disabled={!props.hasWorkspace} onClick={props.submitPatch}>提交补丁</button></section>;
}

function createInitialState(session: DesktopSession, memory: MemorySnapshot | undefined, permissions: PendingPermission[]): BoltState {
  let state = reduceBoltState(createBoltState(), { type: 'workspace.selected', path: session.workspacePath });
  if (session.lastRunId) state = reduceBoltState(state, { type: 'harness.run.created', runId: session.lastRunId });
  if (memory) state = reduceBoltState(state, { type: 'memory.snapshot.loaded', snapshot: memory });
  if (permissions.length) state = reduceBoltState(state, { type: 'permissions.pending.loaded', permissions });
  return state;
}

function FirstRunWizard({ session, onComplete }: { session: DesktopSession; onComplete: (s: DesktopSession) => void }) {
  const [workspacePath, setWorkspacePath] = useState(session.workspacePath || '');
  const [coreUrl, setCoreUrl] = useState(session.coreUrl);
  return (<main className="wizard"><section className="wizardPanel"><div className="brand"><ShieldCheck size={24} /><h1>首次运行</h1></div><label>工作区路径<input aria-label="工作区路径" value={workspacePath} onChange={(e) => setWorkspacePath(e.target.value)} /></label><label>核心服务地址<input aria-label="核心服务地址" value={coreUrl} onChange={(e) => setCoreUrl(e.target.value)} /></label><p>API 密钥不会写入浏览器存储；模型配置继续由 Agent Core 管理。</p><button type="button" onClick={() => onComplete({ completed: true, workspacePath, coreUrl, lastRunId: session.lastRunId })}><FolderOpen size={16} />进入工作台</button></section></main>);
}

function ModelPanel({ model, setModel, apiKey, setApiKey, saveModel, status }: { model: ModelSettings; setModel: (m: ModelSettings) => void; apiKey: string; setApiKey: (v: string) => void; saveModel: () => void; status: BoltState['modelSettingsStatus'] }) {
  return <section className="modelPanel"><label>Provider<input aria-label="Provider" value={model.provider} onChange={(e) => setModel({ ...model, provider: e.target.value })} /></label><label>Base URL<input aria-label="Base URL" value={model.base_url} onChange={(e) => setModel({ ...model, base_url: e.target.value })} /></label><label>Model<input aria-label="Model" value={model.model} onChange={(e) => setModel({ ...model, model: e.target.value })} /></label><label>API 密钥<input aria-label="API 密钥" value={apiKey} onChange={(e) => setApiKey(e.target.value)} /></label><button type="button" onClick={saveModel}>保存模型设置</button><span>{status?.has_api_key ? 'API 密钥已配置' : 'API 密钥未配置'}</span></section>;
}

function TaskLog({ state }: { state: BoltState }) {
  const items = [...state.agentStepResults.map((r) => r.status), ...state.toolResults.map((r) => r.output || r.reason || r.status)];
  return <aside className="panel"><h2>任务日志</h2>{items.length ? items.map((item) => <p key={item}>{item}</p>) : <p>暂无执行结果</p>}</aside>;
}

function TracePanel({ state }: { state: BoltState }) {
  return <aside className="panel"><h2>执行轨迹</h2>{state.traceEvents.length ? state.traceEvents.map((e) => <p key={`${e.sequence}-${e.type}`}>{e.type}</p>) : <p>暂无轨迹事件</p>}</aside>;
}

function DogfoodPanel({ goalInfo, reviewResult, timeline }: { goalInfo: Goal | null; reviewResult: { passed: boolean; failures: string[] } | null; timeline: unknown[] }) {
  return <aside className="panel"><h2>自测工作流</h2>{goalInfo ? <div className="stack"><strong>目标</strong><span>{String(goalInfo.id)}</span><span>{String(goalInfo.status)}</span></div> : <p>暂无目标</p>}{reviewResult ? <div className="stack"><strong>审查</strong><span>{reviewResult.passed ? <CheckCircle2 size={14} /> : '审查失败'}</span>{reviewResult.failures.length ? <span>{reviewResult.failures.join(', ')}</span> : null}</div> : null}{timeline.length ? <div className="stack"><strong>时间线</strong><span>{timeline.length} 事件</span></div> : null}</aside>;
}

function PermissionsPanel({ permissions, onDecision }: { permissions: PendingPermission[]; onDecision: (id: string, approved: boolean) => void }) {
  return <aside className="panel"><h2>待批准权限</h2>{permissions.length ? permissions.map((p) => <PermissionItem key={p.request_id} permission={p} onDecision={onDecision} />) : <p>暂无待批准权限</p>}</aside>;
}

function PermissionItem({ permission, onDecision }: { permission: PendingPermission; onDecision: (id: string, approved: boolean) => void }) {
  const change = permission.payload.change_set as { path?: string; diff?: string } | undefined;
  const command = typeof permission.payload.command === 'string' ? permission.payload.command : '';
  return <div className="stack"><strong>{permission.tool}</strong><span>{permission.operation}</span><span>{permission.reason}</span>{command ? <code>{command}</code> : null}{change ? <pre>{`${change.path}\n${change.diff}`}</pre> : null}<div className="actions"><button type="button" onClick={() => onDecision(permission.request_id, true)}>批准</button><button type="button" onClick={() => onDecision(permission.request_id, false)}>拒绝</button></div></div>;
}

function MemoryPanel({ snapshot }: { snapshot: MemorySnapshot | null }) {
  const perception = snapshot?.records.filter((r) => r.tags?.includes('perception')) ?? [];
  return <aside className="panel"><h2>记忆 / 感知</h2>{perception.length ? perception.map((r) => <PerceptionRecord key={r.id} record={r} />) : <p>暂无记忆</p>}</aside>;
}

function PerceptionRecord({ record }: { record: NonNullable<MemorySnapshot['records'][number]> }) {
  const metadata = record.metadata ?? {};
  const intent = readPath(metadata, ['intent', 'category']);
  const languages = Array.isArray(metadata.languages) ? metadata.languages.join(', ') : '';
  return <div className="stack"><CheckCircle2 size={14} /><strong>{record.scope}</strong><span>{String(metadata.package_manager ?? '')}</span><span>{languages}</span><span>{String(intent ?? '')}</span></div>;
}

function StatusRow({ label, value }: { label: string; value: string }) { return <div className="statusRow"><span>{label}</span><strong>{value}</strong></div>; }

function readPath(value: Record<string, unknown>, path: string[]): unknown { return path.reduce<unknown>((current, key) => isRecord(current) ? current[key] : undefined, value); }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null; }
