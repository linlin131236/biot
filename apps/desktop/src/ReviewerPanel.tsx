/**
 * ReviewerPanel — 独立审查引擎 + 严格 Gate (M161)。
 * 对代码变更执行审查，P0/P1 阻止批准，P2 触发需修改。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useState } from 'react';

interface Props {
  baseUrl: string;
  fetcher?: Fetcher;
  api: {
    reviewOutput: (baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchVerdictLabel: (baseUrl: string, verdict: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'executing' | 'done' | 'error';

interface Finding {
  severity: string;
  category: string;
  description: string;
  location: string;
  suggestion: string;
}

interface ReviewResult {
  findings: Finding[];
  evidence: unknown[];
  tests_status: unknown;
  residual_risks: unknown[];
  verdict: string;
  source_refs: unknown[];
}

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

const VERDICT_LABELS: Record<string, string> = {
  approved: '已批准',
  changes_requested: '需修改',
  blocked: '已阻塞',
};

const VERDICT_COLORS: Record<string, string> = {
  approved: '#16a34a',
  changes_requested: '#d97706',
  blocked: '#dc2626',
};

export function ReviewerPanel({ baseUrl, api, fetcher = fetch }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [codeChanges, setCodeChanges] = useState('');
  const [tests, setTests] = useState('');
  const [evidenceRefs, setEvidenceRefs] = useState('');
  const [sourceRefs, setSourceRefs] = useState('');
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState('');

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError('');
    setCodeChanges('');
    setTests('');
    setEvidenceRefs('');
    setSourceRefs('');
  }

  function handleExecute() {
    if (!codeChanges.trim()) return;
    setError('');
    setPhase('executing');
    const payload: Record<string, unknown> = {
      code_changes: codeChanges.trim(),
      tests: tests.trim(),
      evidence_refs: evidenceRefs.split('\n').map((s) => s.trim()).filter((s) => s.length > 0),
      source_refs: sourceRefs.split('\n').map((s) => s.trim()).filter((s) => s.length > 0),
    };
    api.reviewOutput(baseUrl, payload, fetcher)
      .then((data) => {
        const r = data as Record<string, unknown>;
        const rawFindings = Array.isArray(r.findings) ? r.findings : [];
        const findings: Finding[] = rawFindings.map((f: Record<string, unknown>) => ({
          severity: String(f.severity ?? ''),
          category: String(f.category ?? ''),
          description: String(f.description ?? ''),
          location: String(f.location ?? ''),
          suggestion: String(f.suggestion ?? ''),
        }));
        setResult({
          findings,
          evidence: Array.isArray(r.evidence) ? r.evidence : [],
          tests_status: r.tests_status ?? null,
          residual_risks: Array.isArray(r.residual_risks) ? r.residual_risks : [],
          verdict: String(r.verdict ?? ''),
          source_refs: Array.isArray(r.source_refs) ? r.source_refs : [],
        });
        setPhase('done');
      })
      .catch((e) => {
        setError(`执行审查失败：${e instanceof Error ? e.message : String(e)}`);
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

  if (phase === 'executing') {
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在执行审查...</div>;
  }

  if (phase === 'done' && result) {
    const verdictColor = VERDICT_COLORS[result.verdict] || '#6b7280';
    const verdictLabel = VERDICT_LABELS[result.verdict] || result.verdict;

    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>审查结果</h3>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 3, background: verdictColor, color: '#fff', fontSize: 12, fontWeight: 600 }}>
            {verdictLabel}
          </span>
        </div>

        {result.findings.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>审查发现</div>
            {result.findings.map((f, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: i < result.findings.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
                  <span style={{ padding: '1px 6px', borderRadius: 3, background: f.severity === 'P0' ? '#dc2626' : f.severity === 'P1' ? '#d97706' : '#6b7280', color: '#fff', fontSize: 11, fontWeight: 600 }}>{f.severity}</span>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>{f.category}</span>
                </div>
                <div style={{ marginBottom: 4 }}>{f.description}</div>
                {f.location && <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>位置：{f.location}</div>}
                {f.suggestion && <div style={{ fontSize: 12, color: '#374151' }}>建议：{f.suggestion}</div>}
              </div>
            ))}
          </div>
        )}

        {result.evidence.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>证据引用</div>
            {result.evidence.map((ref, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.evidence.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {typeof ref === 'string' ? ref : JSON.stringify(ref)}
              </div>
            ))}
          </div>
        )}

        {Array.isArray(result.residual_risks) && result.residual_risks.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>剩余风险</div>
            {result.residual_risks.map((risk, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.residual_risks.length - 1 ? '1px solid #f3f4f6' : 'none', color: '#92400e' }}>
                {typeof risk === 'string' ? risk : JSON.stringify(risk)}
              </div>
            ))}
          </div>
        )}

        {result.source_refs.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>来源引用</div>
            {result.source_refs.map((ref, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.source_refs.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {typeof ref === 'string' ? ref : JSON.stringify(ref)}
              </div>
            ))}
          </div>
        )}

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>新建审查</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>审查引擎</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        独立审查，严格 Gate。P0/P1 阻止批准，P2 触发需修改。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>代码变更</label>
        <textarea
          value={codeChanges}
          onChange={(e) => setCodeChanges(e.target.value)}
          rows={6}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="输入代码变更内容"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>测试</label>
        <input
          value={tests}
          onChange={(e) => setTests(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
          placeholder="输入测试命令或结果"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>证据引用</label>
        <textarea
          value={evidenceRefs}
          onChange={(e) => setEvidenceRefs(e.target.value)}
          rows={3}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="每行一个证据引用"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>来源引用</label>
        <textarea
          value={sourceRefs}
          onChange={(e) => setSourceRefs(e.target.value)}
          rows={3}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="每行一个来源引用"
        />
      </div>

      <button
        onClick={handleExecute}
        disabled={!codeChanges.trim()}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #16a34a',
          background: codeChanges.trim() ? '#16a34a' : '#e5e7eb',
          color: codeChanges.trim() ? '#fff' : '#9ca3af',
          cursor: codeChanges.trim() ? 'pointer' : 'not-allowed',
        }}
      >
        执行审查
      </button>
    </div>
  );
}
