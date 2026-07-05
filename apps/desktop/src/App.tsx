import { useReducer, useState } from 'react';
import { AlertTriangle, CheckCircle2, FolderOpen, RefreshCw, ShieldCheck } from 'lucide-react';
import type { MemorySnapshot, PendingPermission } from '@bolt/shared';
import { fetchMemorySnapshot, fetchPendingPermissions } from './harnessClient';
import { createBoltState, reduceBoltState, type BoltState } from './state';
import { loadDesktopSession, saveDesktopSession, type DesktopSession } from './desktopSession';
import './styles.css';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface AppProps {
  fetcher?: Fetcher;
  initialMemorySnapshot?: MemorySnapshot;
  initialPendingPermissions?: PendingPermission[];
}

export function App({ fetcher = fetch, initialMemorySnapshot, initialPendingPermissions = [] }: AppProps) {
  const [session, setSession] = useState<DesktopSession>(() => loadDesktopSession());
  const [error, setError] = useState<string | null>(null);
  const [state, dispatch] = useReducer(reduceBoltState, createInitialState(session, initialMemorySnapshot, initialPendingPermissions));

  function completeFirstRun(next: DesktopSession) {
    saveDesktopSession(next);
    setSession(next);
    dispatch({ type: 'workspace.selected', path: next.workspacePath });
  }

  async function refreshMemory() {
    try {
      setError(null);
      dispatch({ type: 'memory.snapshot.loaded', snapshot: await fetchMemorySnapshot(session.coreUrl, fetcher) });
    } catch {
      setError('无法连接 Agent Core。请确认服务已启动并检查 Core URL。');
    }
  }

  async function refreshPermissions() {
    try {
      setError(null);
      dispatch({ type: 'permissions.pending.loaded', permissions: await fetchPendingPermissions(session.coreUrl, fetcher) });
    } catch {
      setError('无法加载权限请求。请稍后重试。');
    }
  }

  if (!session.completed) return <FirstRunWizard session={session} onComplete={completeFirstRun} />;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><ShieldCheck size={22} /><h1>Bolt</h1></div>
        <StatusRow label="Agent Core" value={state.coreStatus} />
        <StatusRow label="Workspace" value={state.workspacePath || session.workspacePath} />
        <StatusRow label="Core URL" value={session.coreUrl} />
        <StatusRow label="Last run" value={session.lastRunId || 'none'} />
      </aside>
      <section className="workbench">
        <header className="toolbar">
          <span>Workbench</span>
          <div className="actions">
            <button type="button" onClick={refreshMemory}><RefreshCw size={16} />刷新 Memory</button>
            <button type="button" onClick={refreshPermissions}>刷新 Permissions</button>
          </div>
        </header>
        {error ? <div className="error"><AlertTriangle size={16} />{error}</div> : null}
        <div className="message assistant">安全代码助手已就绪。选择任务后，我会先读上下文，再通过 diff 和确认执行修改。</div>
        <section className="panels">
          <TaskLog state={state} />
          <TracePanel state={state} />
          <PermissionsPanel permissions={state.pendingPermissions} />
          <MemoryPanel snapshot={state.memorySnapshot} />
        </section>
      </section>
    </main>
  );
}

function createInitialState(session: DesktopSession, memory: MemorySnapshot | undefined, permissions: PendingPermission[]): BoltState {
  let state = reduceBoltState(createBoltState(), { type: 'workspace.selected', path: session.workspacePath });
  if (memory) state = reduceBoltState(state, { type: 'memory.snapshot.loaded', snapshot: memory });
  if (permissions.length) state = reduceBoltState(state, { type: 'permissions.pending.loaded', permissions });
  return state;
}

function FirstRunWizard({ session, onComplete }: { session: DesktopSession; onComplete: (session: DesktopSession) => void }) {
  const [workspacePath, setWorkspacePath] = useState(session.workspacePath || 'D:/Bolt/Bolt');
  const [coreUrl, setCoreUrl] = useState(session.coreUrl);
  return (
    <main className="wizard">
      <section className="wizardPanel">
        <div className="brand"><ShieldCheck size={24} /><h1>首次运行</h1></div>
        <label>工作区路径<input aria-label="工作区路径" value={workspacePath} onChange={(event) => setWorkspacePath(event.target.value)} /></label>
        <label>Agent Core URL<input aria-label="Agent Core URL" value={coreUrl} onChange={(event) => setCoreUrl(event.target.value)} /></label>
        <p>API Key 不会写入浏览器存储；模型配置继续由 Agent Core 管理。</p>
        <button type="button" onClick={() => onComplete({ completed: true, workspacePath, coreUrl, lastRunId: session.lastRunId })}><FolderOpen size={16} />进入工作台</button>
      </section>
    </main>
  );
}

function TaskLog({ state }: { state: BoltState }) {
  const body = state.agentStepResults.length ? state.agentStepResults.map((result) => result.status).join(', ') : 'No execution results.';
  return <WorkbenchPanel title="Task Log" body={body} />;
}

function TracePanel({ state }: { state: BoltState }) {
  const body = state.traceEvents.length ? state.traceEvents.map((event) => event.type).join('\n') : 'No trace events.';
  return <WorkbenchPanel title="Harness Trace" body={body} />;
}

function PermissionsPanel({ permissions }: { permissions: PendingPermission[] }) {
  return (
    <aside className="panel">
      <h2>Pending Permissions</h2>
      {permissions.length ? permissions.map((permission) => <PermissionItem key={permission.request_id} permission={permission} />) : <p>No pending permission.</p>}
    </aside>
  );
}

function PermissionItem({ permission }: { permission: PendingPermission }) {
  const change = permission.payload.change_set as { path?: string; diff?: string } | undefined;
  return <div className="stack"><strong>{permission.tool}</strong><span>{permission.operation}</span><span>{permission.reason}</span>{change ? <pre>{`${change.path}\n${change.diff}`}</pre> : null}</div>;
}

function MemoryPanel({ snapshot }: { snapshot: MemorySnapshot | null }) {
  const perception = snapshot?.records.filter((record) => record.tags?.includes('perception')) ?? [];
  return (
    <aside className="panel">
      <h2>Memory / Perception</h2>
      {perception.length ? perception.map((record) => <PerceptionRecord key={record.id} record={record} />) : <p>No memories loaded.</p>}
    </aside>
  );
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
