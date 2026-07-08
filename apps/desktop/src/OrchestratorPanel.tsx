/**
 * OrchestratorPanel — 编排器 (M163)。
 * 串联 5 个角色：规划师 → 研究员 → 构建师 → 审查员 → 技能学习器。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface RoleInfo {
  role_key: string;
  label_cn: string;
  status: string;
}

interface OrchestratorResult {
  task_description: string;
  rounds: number;
  final_verdict: string;
  builder_output?: Record<string, unknown>;
  review_findings?: Array<Record<string, unknown>>;
  proposals?: Array<Record<string, unknown>>;
  trace?: Array<Record<string, unknown>>;
}

interface Props {
  baseUrl: string;
  api: {
    runOrchestration: (baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchRoles: (baseUrl: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'running' | 'done' | 'error';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

const ROLE_ORDER = ['planner', 'researcher', 'builder', 'reviewer', 'skill_learner'];

const ROLE_LABELS: Record<string, string> = {
  planner: '规划师',
  researcher: '研究员',
  builder: '构建师',
  reviewer: '审查员',
  skill_learner: '技能学习器',
};

const VERDICT_COLORS: Record<string, string> = {
  approved: '#16a34a',
  blocked: '#dc2626',
  failed: '#d97706',
};

const STATUS_COLORS: Record<string, string> = {
  ready: '#6b7280',
  running: '#2563eb',
  completed: '#16a34a',
  failed: '#dc2626',
};

export function OrchestratorPanel({ baseUrl, api }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [taskDescription, setTaskDescription] = useState('');
  const [workspace, setWorkspace] = useState('');
  const [result, setResult] = useState<OrchestratorResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.fetchRoles(baseUrl, window.fetch)
      .then((data) => {
        if (cancelled) return;
        const raw = (data as Record<string, unknown>).roles as Array<Record<string, unknown>> | undefined;
        if (raw && raw.length > 0) {
          const mapped: RoleInfo[] = raw.map((r) => ({
            role_key: String(r.role_key ?? r.key ?? ''),
            label_cn: String(r.label_cn ?? r.label ?? ROLE_LABELS[r.role_key ?? ''] ?? r.role_key ?? ''),
            status: String(r.status ?? 'ready'),
          }));
          setRoles(mapped);
        } else {
          setRoles(
            ROLE_ORDER.map((key) => ({
              role_key: key,
              label_cn: ROLE_LABELS[key] ?? key,
              status: 'ready',
            }))
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRoles(
            ROLE_ORDER.map((key) => ({
              role_key: key,
              label_cn: ROLE_LABELS[key] ?? key,
              status: 'ready',
            }))
          );
        }
      });
    return () => { cancelled = true; };
  }, [baseUrl, api]);

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError('');
    setTaskDescription('');
    setWorkspace('');
  }

  function handleRun() {
    if (!taskDescription.trim() || !workspace.trim()) return;
    setError('');
    setPhase('running');
    setResult(null);
    api.runOrchestration(baseUrl, { task_description: taskDescription.trim(), workspace: workspace.trim() }, window.fetch)
      .then((data) => {
        const r = data as Record<string, unknown>;
        const trace = Array.isArray(r.trace) ? (r.trace as Array<Record<string, unknown>>) : [];
        const updatedRoles = roles.map((role) => {
          const matching = trace.find((t) => String(t.role ?? '') === role.role_key);
          if (matching) {
            return {
              ...role,
              status: String(matching.status ?? 'completed'),
            };
          }
          return role;
        });
        setRoles(updatedRoles);
        setResult({
          task_description: String(r.task_description ?? taskDescription.trim()),
          rounds: typeof r.rounds === 'number' ? (r.rounds as number) : trace.length,
          final_verdict: String(r.final_verdict ?? 'failed'),
          builder_output: (r.builder_output as Record<string, unknown>) || undefined,
          review_findings: Array.isArray(r.review_findings) ? (r.review_findings as Array<Record<string, unknown>>) : undefined,
          proposals: Array.isArray(r.proposals) ? (r.proposals as Array<Record<string, unknown>>) : undefined,
          trace,
        });
        setPhase('done');
      })
      .catch((e) => {
        setError(`运行编排失败：${e instanceof Error ? e.message : String(e)}`);
        setPhase('error');
      });
  }

  if (error) {
    return (
      <div style={{ padding: '1rem', color: '#c44' }}>
        {error}
        <button onClick={handleReset} style={{ marginLeft: 12, padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>重试</button>
      </div>
    );
  }

  if (phase === 'running') {
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在执行编排流程...</div>;
  }

  if (phase === 'done' && result) {
    const builderOutput = result.builder_output as Record<string, unknown> | undefined;
    const builderSummary = typeof builderOutput?.summary === 'string'
      ? String(builderOutput.summary)
      : typeof builderOutput?.output === 'string'
        ? String(builderOutput.output)
        : typeof builderOutput?.task_id === 'string'
          ? `任务 ${builderOutput.task_id}`
          : '无摘要';

    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>编排结果</h3>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>任务：{result.task_description}</div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <div>
              <span style={{ fontSize: 12, color: '#6b7280', marginRight: 4 }}>裁决：</span>
              <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 3, background: VERDICT_COLORS[result.final_verdict] || '#6b7280', color: '#fff', fontSize: 12, fontWeight: 600 }}>{result.final_verdict}</span>
            </div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>轮次：{result.rounds}</div>
          </div>
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>构建输出</div>
          <div style={{ whiteSpace: 'pre-wrap' }}>{builderSummary || '无内容'}</div>
        </div>

        {result.review_findings && result.review_findings.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>审查发现</div>
            {result.review_findings.map((finding, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.review_findings!.length - 1 ? '1px solid #f3f4f6' : 'none', fontSize: 12 }}>
                {typeof finding === 'string' ? finding : JSON.stringify(finding)}
              </div>
            ))}
          </div>
        )}

        {result.proposals && result.proposals.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>提案</div>
            {result.proposals.map((proposal, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.proposals!.length - 1 ? '1px solid #f3f4f6' : 'none', fontSize: 12 }}>
                {typeof proposal === 'string' ? proposal : JSON.stringify(proposal)}
              </div>
            ))}
          </div>
        )}

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>新建编排</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>编排器</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        串联 5 个角色：规划师 → 研究员 → 构建师 → 审查员 → 技能学习器
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        {roles.map((role) => (
          <div key={role.role_key} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '6px 10px', fontSize: 12 }}>
            <span>{role.label_cn}</span>
            <span style={{ display: 'inline-block', padding: '1px 6px', borderRadius: 3, background: STATUS_COLORS[role.status] || '#6b7280', color: '#fff', fontSize: 11, fontWeight: 600 }}>{role.status}</span>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>任务描述</label>
        <textarea
          value={taskDescription}
          onChange={(e) => setTaskDescription(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="输入任务描述"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>工作区</label>
        <input
          value={workspace}
          onChange={(e) => setWorkspace(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
          placeholder="输入工作区路径"
        />
      </div>

      <button
        onClick={handleRun}
        disabled={!taskDescription.trim() || !workspace.trim()}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #16a34a',
          background: (!taskDescription.trim() || !workspace.trim()) ? '#e5e7eb' : '#16a34a',
          color: (!taskDescription.trim() || !workspace.trim()) ? '#9ca3af' : '#fff',
          cursor: (!taskDescription.trim() || !workspace.trim()) ? 'not-allowed' : 'pointer',
        }}
      >
        运行编排
      </button>
    </div>
  );
}
