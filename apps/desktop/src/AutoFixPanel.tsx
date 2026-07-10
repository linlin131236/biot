/**
 * AutoFixPanel — 自动修复 (M167)。
 * 对审查发现执行自动修复并展示结果。
 * 纯前端控制，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface Props {
  fetcher?: Fetcher;
  api: {
    autoFixReviewFindings: (payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'running' | 'done' | 'error';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface FixResult {
  fixed?: number;
  remaining?: number;
  fixed_items?: Array<Record<string, unknown>>;
  remaining_items?: Array<Record<string, unknown>>;
  message?: string;
}

export function AutoFixPanel({ fetcher, api }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [findingsJson, setFindingsJson] = useState('');
  const [codeChanges, setCodeChanges] = useState('');
  const [result, setResult] = useState<FixResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAutoFix() {
    setError(null);
    setResult(null);
    setPhase('running');
    let parsedFindings: unknown = [];
    try {
      parsedFindings = findingsJson.trim() ? JSON.parse(findingsJson) : [];
    } catch {
      setError('findings JSON 格式无效，请检查输入。');
      setPhase('error');
      return;
    }
    try {
      const res = await api.autoFixReviewFindings({
        findings: parsedFindings,
        code_changes: codeChanges.trim(),
      }, fetcher);
      const r = res as Record<string, unknown>;
      setResult({
        fixed: typeof r.fixed === 'number' ? (r.fixed as number) : 0,
        remaining: typeof r.remaining === 'number' ? (r.remaining as number) : 0,
        fixed_items: Array.isArray(r.fixed_items) ? (r.fixed_items as Array<Record<string, unknown>>) : [],
        remaining_items: Array.isArray(r.remaining_items) ? (r.remaining_items as Array<Record<string, unknown>>) : [],
        message: typeof r.message === 'string' ? (r.message as string) : '',
      });
      setPhase('done');
    } catch (e) {
      setError(`自动修复失败：${e instanceof Error ? e.message : String(e)}`);
      setPhase('error');
    }
  }

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError(null);
    setFindingsJson('');
    setCodeChanges('');
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
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在自动修复...</div>;
  }

  if (phase === 'done' && result) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>修复结果</h3>

        {result.message && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12, color: '#666', fontSize: 12 }}>
            {result.message}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '8px 12px', flex: 1 }}>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>已修复</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{result.fixed ?? 0}</div>
          </div>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '8px 12px', flex: 1 }}>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>剩余</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{result.remaining ?? 0}</div>
          </div>
        </div>

        {result.fixed_items && result.fixed_items.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>已修复项</div>
            {result.fixed_items.map((item, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.fixed_items!.length - 1 ? '1px solid #f3f4f6' : 'none', fontSize: 12 }}>
                {typeof item === 'string' ? item : JSON.stringify(item)}
              </div>
            ))}
          </div>
        )}

        {result.remaining_items && result.remaining_items.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>剩余项</div>
            {result.remaining_items.map((item, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.remaining_items!.length - 1 ? '1px solid #f3f4f6' : 'none', fontSize: 12 }}>
                {typeof item === 'string' ? item : JSON.stringify(item)}
              </div>
            ))}
          </div>
        )}

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>重新修复</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>自动修复</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        对审查发现执行自动修复。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>findings JSON（可选，数组格式）</label>
        <textarea
          value={findingsJson}
          onChange={(e) => setFindingsJson(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder='[{"severity": "P0", "description": "示例问题"}]'
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>code_changes（可选）</label>
        <textarea
          value={codeChanges}
          onChange={(e) => setCodeChanges(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="输入代码变更内容"
        />
      </div>

      <button
        onClick={handleAutoFix}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #2563eb',
          background: '#2563eb',
          color: '#fff',
          cursor: 'pointer',
        }}
      >
        自动修复
      </button>
    </div>
  );
}
