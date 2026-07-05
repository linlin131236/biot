import { ShieldCheck } from 'lucide-react';
import './styles.css';

const initialMessage = '安全代码助手已就绪。选择工作区后，我会先读上下文，再通过 diff 和确认执行修改。';

export function App() {
  return (
    <main className="shell">
      <section className="sidebar">
        <div className="brand">
          <ShieldCheck size={22} />
          <h1>Bolt</h1>
        </div>
        <StatusRow label="Agent Core" value="unknown" />
        <StatusRow label="Workspace" value="No workspace selected" />
      </section>
      <section className="workbench">
        <header className="toolbar">
          <span>Chat</span>
          <button type="button">Select Workspace</button>
        </header>
        <div className="message assistant">{initialMessage}</div>
        <section className="panels">
          <WorkbenchPanel title="Task Log" body="No execution results." />
          <WorkbenchPanel title="Harness Trace" body="No trace events." />
          <WorkbenchPanel title="Pending Permissions" body="No pending permission." />
          <WorkbenchPanel title="Memory" body="No memories loaded." />
        </section>
      </section>
    </main>
  );
}

function WorkbenchPanel({ title, body }: { title: string; body: string }) {
  return (
    <aside className="panel">
      <h2>{title}</h2>
      <p>{body}</p>
    </aside>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="statusRow">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
