import { useReducer, useState } from 'react';
import { AlertTriangle, CheckCircle2, FolderOpen, RefreshCw, ShieldCheck } from 'lucide-react';
import type { MemorySnapshot, ModelSettings, PendingPermission, ToolResult } from '@bolt/shared';
import { fetchHarnessTrace, fetchMemorySnapshot, fetchPendingPermissions } from './harnessClient';
import { createBoltState, reduceBoltState, type BoltState } from './state';
import { loadDesktopSession, saveDesktopSession, type DesktopSession } from './desktopSession';
import { decidePermission, executeWorkflowStep, loadModelSettings, maintainMemory, refreshWorkflow, startWorkflowRun, storeModelSettings } from './workflowClient';
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
  const runId = state.currentRunId || session.lastRunId;

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
      const run = await startWorkflowRun(session.coreUrl, goal || 'Continue Bolt task', fetcher);
      dispatch({ type: 'harness.run.created', runId: run.id });
      saveSession({ ...session, lastRunId: run.id });
    }, '无法创建任务。');
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

  function applyRefresh(refresh: { trace?: BoltState['traceEvents']; memory?: MemorySnapshot; permissions?: PendingPermission[] }) {
    if (refresh.trace) dispatch({ type: 'harness.trace.loaded', events: refresh.trace });
    if (refresh.memory) dispatch({ type: 'memory.snapshot.loaded', snapshot: refresh.memory });
    if (refresh.permissions) dispatch({ type: 'permissions.pending.loaded', permissions: refresh.permissions });
  }

  function recordToolResult(result: ToolResult) {
    dispatch({ type: 'tool.result.recorded', result });
  }

  function saveSession(next: DesktopSession) {
    saveDesktopSession(next);
    setSession(next);
  }

  if (!session.completed) return <FirstRunWizard session={session} onComplete={completeFirstRun} />;

  return <main className="shell"><aside className="sidebar"><div className="brand"><ShieldCheck size={22} /><h1>Bolt</h1></div><StatusRow label="Agent Core" value={state.coreStatus} /><StatusRow label="Workspace" value={state.workspacePath || session.workspacePath} /><StatusRow label="Core URL" value={session.coreUrl} /><StatusRow label="Last run" value={runId || 'none'} /></aside><section className="workbench"><Toolbar goal={goal} setGoal={setGoal} runId={runId} startRun={startRun} runStep={runStep} refreshTrace={refreshTraceOnly} refreshMemory={refreshMemory} refreshPermissions={refreshPermissions} runGardener={runGardener} />{error ? <div className="error"><AlertTriangle size={16} />{error}</div> : null}<ModelPanel model={model} setModel={setModel} apiKey={apiKey} setApiKey={setApiKey} saveModel={saveModel} status={state.modelSettingsStatus} /><section className="panels"><TaskLog state={state} /><TracePanel state={state} /><PermissionsPanel permissions={state.pendingPermissions} onDecision={onPermission} /><MemoryPanel snapshot={state.memorySnapshot} /></section></section></main>;
}

function Toolbar(props: { goal: string; setGoal: (value: string) => void; runId: string | null; startRun: () => void; runStep: () => void; refreshTrace: () => void; refreshMemory: () => void; refreshPermissions: () => void; runGardener: () => void }) {
  return <header className="toolbar"><label>任务目标<input aria-label="任务目标" value={props.goal} onChange={(event) => props.setGoal(event.target.value)} /></label><div className="actions"><button type="button" onClick={props.startRun}>Start Run</button><button type="button" disabled={!props.runId} onClick={props.runStep}>Run Step</button><button type="button" disabled={!props.runId} onClick={props.refreshTrace}>Refresh Trace</button><button type="button" onClick={props.refreshMemory}><RefreshCw size={16} />刷新 Memory</button><button type="button" onClick={props.refreshPermissions}>刷新 Permissions</button><button type="button" disabled={!props.runId} onClick={props.runGardener}>Run Document Gardener</button></div></header>;
}

function createInitialState(session: DesktopSession, memory: MemorySnapshot | undefined, permissions: PendingPermission[]): BoltState {
  let state = reduceBoltState(createBoltState(), { type: 'workspace.selected', path: session.workspacePath });
  if (session.lastRunId) state = reduceBoltState(state, { type: 'harness.run.created', runId: session.lastRunId });
  if (memory) state = reduceBoltState(state, { type: 'memory.snapshot.loaded', snapshot: memory });
  if (permissions.length) state = reduceBoltState(state, { type: 'permissions.pending.loaded', permissions });
  return state;
}

function FirstRunWizard({ session, onComplete }: { session: DesktopSession; onComplete: (session: DesktopSession) => void }) {
  const [workspacePath, setWorkspacePath] = useState(session.workspacePath || 'D:/Bolt/Bolt');
  const [coreUrl, setCoreUrl] = useState(session.coreUrl);
  return <main className="wizard"><section className="wizardPanel"><div className="brand"><ShieldCheck size={24} /><h1>首次运行</h1></div><label>工作区路径<input aria-label="工作区路径" value={workspacePath} onChange={(event) => setWorkspacePath(event.target.value)} /></label><label>Agent Core URL<input aria-label="Agent Core URL" value={coreUrl} onChange={(event) => setCoreUrl(event.target.value)} /></label><p>API Key 不会写入浏览器存储；模型配置继续由 Agent Core 管理。</p><button type="button" onClick={() => onComplete({ completed: true, workspacePath, coreUrl, lastRunId: session.lastRunId })}><FolderOpen size={16} />进入工作台</button></section></main>;
}

function ModelPanel({ model, setModel, apiKey, setApiKey, saveModel, status }: { model: ModelSettings; setModel: (model: ModelSettings) => void; apiKey: string; setApiKey: (value: string) => void; saveModel: () => void; status: BoltState['modelSettingsStatus'] }) {
  return <section className="modelPanel"><label>Provider<input aria-label="Provider" value={model.provider} onChange={(event) => setModel({ ...model, provider: event.target.value })} /></label><label>Base URL<input aria-label="Base URL" value={model.base_url} onChange={(event) => setModel({ ...model, base_url: event.target.value })} /></label><label>Model<input aria-label="Model" value={model.model} onChange={(event) => setModel({ ...model, model: event.target.value })} /></label><label>API Key<input aria-label="API Key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} /></label><button type="button" onClick={saveModel}>Save Model Settings</button><span>{status?.has_api_key ? 'API key configured' : 'API key not configured'}</span></section>;
}

function TaskLog({ state }: { state: BoltState }) {
  const items = [...state.agentStepResults.map((result) => result.status), ...state.toolResults.map((result) => result.output || result.reason || result.status)];
  return <aside className="panel"><h2>Task Log</h2>{items.length ? items.map((item) => <p key={item}>{item}</p>) : <p>No execution results.</p>}</aside>;
}

function TracePanel({ state }: { state: BoltState }) {
  return <aside className="panel"><h2>Harness Trace</h2>{state.traceEvents.length ? state.traceEvents.map((event) => <p key={`${event.sequence}-${event.type}`}>{event.type}</p>) : <p>No trace events.</p>}</aside>;
}

function PermissionsPanel({ permissions, onDecision }: { permissions: PendingPermission[]; onDecision: (requestId: string, approved: boolean) => void }) {
  return <aside className="panel"><h2>Pending Permissions</h2>{permissions.length ? permissions.map((permission) => <PermissionItem key={permission.request_id} permission={permission} onDecision={onDecision} />) : <p>No pending permission.</p>}</aside>;
}

function PermissionItem({ permission, onDecision }: { permission: PendingPermission; onDecision: (requestId: string, approved: boolean) => void }) {
  const change = permission.payload.change_set as { path?: string; diff?: string } | undefined;
  const command = typeof permission.payload.command === 'string' ? permission.payload.command : '';
  return <div className="stack"><strong>{permission.tool}</strong><span>{permission.operation}</span><span>{permission.reason}</span>{command ? <code>{command}</code> : null}{change ? <pre>{`${change.path}\n${change.diff}`}</pre> : null}<div className="actions"><button type="button" onClick={() => onDecision(permission.request_id, true)}>Approve</button><button type="button" onClick={() => onDecision(permission.request_id, false)}>Reject</button></div></div>;
}

function MemoryPanel({ snapshot }: { snapshot: MemorySnapshot | null }) {
  const perception = snapshot?.records.filter((record) => record.tags?.includes('perception')) ?? [];
  return <aside className="panel"><h2>Memory / Perception</h2>{perception.length ? perception.map((record) => <PerceptionRecord key={record.id} record={record} />) : <p>No memories loaded.</p>}</aside>;
}

function PerceptionRecord({ record }: { record: NonNullable<MemorySnapshot['records'][number]> }) {
  const metadata = record.metadata ?? {};
  const intent = readPath(metadata, ['intent', 'category']);
  const languages = Array.isArray(metadata.languages) ? metadata.languages.join(', ') : '';
  const scheduler = Array.isArray(metadata.scheduler) ? metadata.scheduler.map((item) => isRecord(item) ? item.status : '').join(', ') : '';
  return <div className="stack"><CheckCircle2 size={14} /><strong>{record.scope}</strong><span>{String(metadata.package_manager ?? '')}</span><span>{languages}</span><span>{String(intent ?? '')}</span><span>{scheduler}</span></div>;
}

function WorkbenchPanel({ title, body }: { title: string; body: string }) {
  return <aside className="panel"><h2>{title}</h2><p>{body}</p></aside>;
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
