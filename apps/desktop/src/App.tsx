import { useEffect, useReducer, useState } from 'react';
import { AlertTriangle, CheckCircle2, FolderOpen, RefreshCw, ShieldCheck } from 'lucide-react';
import type { MemorySnapshot, ModelSettings, PendingPermission, ToolResult } from '@bolt/shared';
import { fetchHarnessTrace, fetchMemorySnapshot, fetchPendingPermissions } from './harnessClient';
import { createBoltState, reduceBoltState, type BoltState } from './state';
import { loadDesktopSession, saveDesktopSession, type DesktopSession } from './desktopSession';
import { fetchCoreHealth } from './coreClient';
import { decidePermission, evaluateWorkflowReview, executeWorkflowStep, loadModelSettings, maintainMemory, refreshWorkflow, startWorkflowRun, storeModelSettings, createWorkflowGoal, fetchWorkflowTimeline } from './workflowClient';
import './styles.css';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface AppProps {
  fetcher?: Fetcher;
  initialMemorySnapshot?: MemorySnapshot;
  initialPendingPermissions?: PendingPermission[];
}

export function App({ fetcher = fetch, initialMemorySnapshot, initialPendingPermissions = [] }: AppProps) {
  const [session, setSession] = useState<DesktopSession>(() => loadDesktopSession());
  const [goal, setGoal] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<ModelSettings>({ provider: 'openai-compatible', base_url: 'http://localhost:11434/v1', model: 'fake-model', temperature: 0.2 });
  const [apiKey, setApiKey] = useState('');
  const [state, dispatch] = useReducer(reduceBoltState, createInitialState(session, initialMemorySnapshot, initialPendingPermissions));
  const [goalInfo, setGoalInfo] = useState<Record<string, unknown> | null>(null);
  const [reviewResult, setReviewResult] = useState<{ passed: boolean; failures: string[] } | null>(null);
  const [timeline, setTimeline] = useState<unknown[]>([]);
  const runId = state.currentRunId || session.lastRunId;

  useEffect(() => {
    if (!session.completed) return;
    let active = true;
    fetchCoreHealth(session.coreUrl, fetcher).then((status) => {
      if (active) dispatch({ type: 'core.health.changed', status });
    });
    return () => { active = false; };
  }, [fetcher, session.completed, session.coreUrl]);

  function completeFirstRun(next: DesktopSession) {
    saveSession(next);
    dispatch({ type: 'workspace.selected', path: next.workspacePath });
  }

  async function guarded(action: () => Promise<void>, fallback: string) {
    try {
      setError(null);
      await action();
    } catch (err) {
      const message = err instanceof Error && err.message.startsWith('Agent Core request failed') ? err.message : fallback;
      setError(message);
    }
  }

  async function startRun() {
    await guarded(async () => {
      const run = await startWorkflowRun(session.coreUrl, goal || 'Continue Bolt task', session.workspacePath, fetcher);
      dispatch({ type: 'harness.run.created', runId: run.id });
      saveSession({ ...session, lastRunId: run.id });
    }, '无法创建任务。');
  }

  async function createGoal() {
    await guarded(async () => {
      const g = await createWorkflowGoal(session.coreUrl, {
        objective: goal || 'Bolt task',
        criteria: ['file read', 'patch approved'],
        max_steps: 10, max_cost: 5.0, max_wall_time: 300,
        workspace: session.workspacePath,
      }, fetcher);
      setGoalInfo(g);
    }, '无法创建目标。');
  }

  async function runStep() {
    if (!runId) return;
    await guarded(async () => {
      const { step, refresh } = await executeWorkflowStep(session.coreUrl, runId, fetcher);
      dispatch({ type: 'agent.step.recorded', result: step });
      if (step.tool_result) dispatch({ type: 'tool.result.recorded', result: step.tool_result });
      applyRefresh(refresh);
    }, '无法执行 Agent Step。');
  }

  async function refreshTraceOnly() {
    if (!runId) return;
    await guarded(async () => dispatch({ type: 'harness.trace.loaded', events: await fetchHarnessTrace(session.coreUrl, runId, fetcher) }), '无法刷新 Trace。');
  }

  async function refreshMemory() {
    await guarded(async () => dispatch({ type: 'memory.snapshot.loaded', snapshot: await fetchMemorySnapshot(session.coreUrl, fetcher) }), '无法连接 Agent Core。请确认服务已启动并检查 Core URL。');
  }

  async function refreshPermissions() {
    await guarded(async () => dispatch({ type: 'permissions.pending.loaded', permissions: await fetchPendingPermissions(session.coreUrl, fetcher) }), '无法加载权限请求。请稍后重试。');
  }

  async function onPermission(requestId: string, approved: boolean) {
    await guarded(async () => {
      const result = await decidePermission(session.coreUrl, requestId, approved, fetcher);
      dispatch({ type: 'tool.result.recorded', result });
      if (runId) applyRefresh(await refreshWorkflow(session.coreUrl, runId, fetcher));
    }, '无法处理权限请求。');
  }

  async function saveModel() {
    await guarded(async () => {
      const status = await storeModelSettings(session.coreUrl, { ...model, api_key: apiKey || undefined }, fetcher);
      dispatch({ type: 'model.settings.loaded', status });
      setApiKey('');
    }, '无法保存模型设置。');
  }

  async function runGardener() {
    if (!runId) return;
    await guarded(async () => recordToolResult(await maintainMemory(session.coreUrl, runId, fetcher)), '无法运行文档园丁。');
  }

  async function fetchTimeline() {
    if (!runId) return;
    await guarded(async () => setTimeline(await fetchWorkflowTimeline(session.coreUrl, runId, fetcher)), '无法加载 Timeline。');
  }

  async function runReview() {
    await guarded(async () => {
      const result = await evaluateWorkflowReview(session.coreUrl, { items: ['pytest', 'build'], results: { pytest: true, build: true } }, fetcher);
      setReviewResult(result);
    }, '无法评估 Review。');
  }

  function applyRefresh(refresh: { trace?: BoltState['traceEvents']; memory?: MemorySnapshot; permissions?: PendingPermission[] }) {
    if (refresh.trace) dispatch({ type: 'harness.trace.loaded', events: refresh.trace });
    if (refresh.memory) dispatch({ type: 'memory.snapshot.loaded', snapshot: refresh.memory });
    if (refresh.permissions) dispatch({ type: 'permissions.pending.loaded', permissions: refresh.permissions });
  }

  function recordToolResult(result: ToolResult) { dispatch({ type: 'tool.result.recorded', result }); }
  function saveSession(next: DesktopSession) { saveDesktopSession(next); setSession(next); }

  if (!session.completed) return <FirstRunWizard session={session} onComplete={completeFirstRun} />;

  return <main className="shell"><aside className="sidebar"><div className="brand"><ShieldCheck size={22} /><h1>Bolt</h1></div><StatusRow label="Agent Core" value={state.coreStatus} /><StatusRow label="Workspace" value={state.workspacePath || session.workspacePath} /><StatusRow label="Core URL" value={session.coreUrl} /><StatusRow label="Last run" value={runId || 'none'} /></aside><section className="workbench"><Toolbar goal={goal} setGoal={setGoal} runId={runId} startRun={startRun} createGoal={createGoal} runStep={runStep} refreshTrace={refreshTraceOnly} refreshMemory={refreshMemory} refreshPermissions={refreshPermissions} runGardener={runGardener} fetchTimeline={fetchTimeline} runReview={runReview} />{error ? <div className="error"><AlertTriangle size={16} />{error}</div> : null}<ModelPanel model={model} setModel={setModel} apiKey={apiKey} setApiKey={setApiKey} saveModel={saveModel} status={state.modelSettingsStatus} /><section className="panels"><TaskLog state={state} /><TracePanel state={state} /><DogfoodPanel goalInfo={goalInfo} reviewResult={reviewResult} timeline={timeline} /><PermissionsPanel permissions={state.pendingPermissions} onDecision={onPermission} /><MemoryPanel snapshot={state.memorySnapshot} /></section></section></main>;
}

function Toolbar(props: { goal: string; setGoal: (v: string) => void; runId: string | null; startRun: () => void; createGoal: () => void; runStep: () => void; refreshTrace: () => void; refreshMemory: () => void; refreshPermissions: () => void; runGardener: () => void; fetchTimeline: () => void; runReview: () => void }) {
  return <header className="toolbar"><label>任务目标<input aria-label="任务目标" value={props.goal} onChange={(e) => props.setGoal(e.target.value)} /></label><div className="actions"><button type="button" onClick={props.startRun}>Start Run</button><button type="button" onClick={props.createGoal}>Create Goal</button><button type="button" disabled={!props.runId} onClick={props.runStep}>Run Step</button><button type="button" disabled={!props.runId} onClick={props.refreshTrace}>Refresh Trace</button><button type="button" onClick={props.refreshMemory}><RefreshCw size={16} />刷新 Memory</button><button type="button" onClick={props.refreshPermissions}>刷新 Permissions</button><button type="button" disabled={!props.runId} onClick={props.runGardener}>Run Gardener</button><button type="button" disabled={!props.runId} onClick={props.fetchTimeline}>Timeline</button><button type="button" onClick={props.runReview}>Review</button></div></header>;
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
  return (<main className="wizard"><section className="wizardPanel"><div className="brand"><ShieldCheck size={24} /><h1>首次运行</h1></div><label>工作区路径<input aria-label="工作区路径" value={workspacePath} onChange={(e) => setWorkspacePath(e.target.value)} /></label><label>Agent Core URL<input aria-label="Agent Core URL" value={coreUrl} onChange={(e) => setCoreUrl(e.target.value)} /></label><p>API Key 不会写入浏览器存储；模型配置继续由 Agent Core 管理。</p><button type="button" onClick={() => onComplete({ completed: true, workspacePath, coreUrl, lastRunId: session.lastRunId })}><FolderOpen size={16} />进入工作台</button></section></main>);
}

function ModelPanel({ model, setModel, apiKey, setApiKey, saveModel, status }: { model: ModelSettings; setModel: (m: ModelSettings) => void; apiKey: string; setApiKey: (k: string) => void; saveModel: () => void; status: BoltState['modelSettingsStatus'] }) {
  return <section className="modelPanel"><label>Provider<input aria-label="Provider" value={model.provider} onChange={(e) => setModel({ ...model, provider: e.target.value })} /></label><label>Base URL<input aria-label="Base URL" value={model.base_url} onChange={(e) => setModel({ ...model, base_url: e.target.value })} /></label><label>Model<input aria-label="Model" value={model.model} onChange={(e) => setModel({ ...model, model: e.target.value })} /></label><label>API Key<input aria-label="API Key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} /></label><button type="button" onClick={saveModel}>Save Model Settings</button><span>{status?.has_api_key ? 'API key configured' : 'API key not configured'}</span></section>;
}

function TaskLog({ state }: { state: BoltState }) {
  const items = [...state.agentStepResults.map((r) => r.status), ...state.toolResults.map((r) => r.output || r.reason || r.status)];
  return <aside className="panel"><h2>Task Log</h2>{items.length ? items.map((item) => <p key={item}>{item}</p>) : <p>No execution results.</p>}</aside>;
}

function TracePanel({ state }: { state: BoltState }) {
  return <aside className="panel"><h2>Harness Trace</h2>{state.traceEvents.length ? state.traceEvents.map((e) => <p key={`${e.sequence}-${e.type}`}>{e.type}</p>) : <p>No trace events.</p>}</aside>;
}

function DogfoodPanel({ goalInfo, reviewResult, timeline }: { goalInfo: Record<string, unknown> | null; reviewResult: { passed: boolean; failures: string[] } | null; timeline: unknown[] }) {
  return <aside className="panel"><h2>Dogfood</h2>{goalInfo ? <div className="stack"><strong>Goal</strong><span>{String(goalInfo.id)}</span><span>{String(goalInfo.status)}</span></div> : <p>No goal created.</p>}{reviewResult ? <div className="stack"><strong>Review</strong><span>{reviewResult.passed ? <CheckCircle2 size={14} /> : 'FAIL'}</span>{reviewResult.failures.length ? <span>{reviewResult.failures.join(', ')}</span> : null}</div> : null}{timeline.length ? <div className="stack"><strong>Timeline</strong><span>{timeline.length} events</span></div> : null}</aside>;
}

function PermissionsPanel({ permissions, onDecision }: { permissions: PendingPermission[]; onDecision: (id: string, approved: boolean) => void }) {
  return <aside className="panel"><h2>Pending Permissions</h2>{permissions.length ? permissions.map((p) => <PermissionItem key={p.request_id} permission={p} onDecision={onDecision} />) : <p>No pending permission.</p>}</aside>;
}

function PermissionItem({ permission, onDecision }: { permission: PendingPermission; onDecision: (id: string, approved: boolean) => void }) {
  const change = permission.payload.change_set as { path?: string; diff?: string } | undefined;
  const command = typeof permission.payload.command === 'string' ? permission.payload.command : '';
  return <div className="stack"><strong>{permission.tool}</strong><span>{permission.operation}</span><span>{permission.reason}</span>{command ? <code>{command}</code> : null}{change ? <pre>{`${change.path}\n${change.diff}`}</pre> : null}<div className="actions"><button type="button" onClick={() => onDecision(permission.request_id, true)}>Approve</button><button type="button" onClick={() => onDecision(permission.request_id, false)}>Reject</button></div></div>;
}

function MemoryPanel({ snapshot }: { snapshot: MemorySnapshot | null }) {
  const perception = snapshot?.records.filter((r) => r.tags?.includes('perception')) ?? [];
  return <aside className="panel"><h2>Memory / Perception</h2>{perception.length ? perception.map((r) => <PerceptionRecord key={r.id} record={r} />) : <p>No memories loaded.</p>}</aside>;
}

function PerceptionRecord({ record }: { record: NonNullable<MemorySnapshot['records'][number]> }) {
  const metadata = record.metadata ?? {};
  const intent = readPath(metadata, ['intent', 'category']);
  const languages = Array.isArray(metadata.languages) ? metadata.languages.join(', ') : '';
  return <div className="stack"><CheckCircle2 size={14} /><strong>{record.scope}</strong><span>{String(metadata.package_manager ?? '')}</span><span>{languages}</span><span>{String(intent ?? '')}</span></div>;
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return <div className="statusRow"><span>{label}</span><strong>{value}</strong></div>;
}

function readPath(value: Record<string, unknown>, path: string[]): unknown {
  return path.reduce<unknown>((current, key) => isRecord(current) ? current[key] : undefined, value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
