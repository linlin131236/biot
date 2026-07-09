/**
 * ToolVerificationPanel — 工具验证 (M166)。
 * 验证工具链可用性并展示结果。
 * 纯只读 UI，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface ToolResult {
  tool_name: string;
  status: string;
  message: string;
}

interface Props {
  baseUrl: string;
  fetcher?: Fetcher;
  api: {
    verifyTools: (baseUrl: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'idle' | 'running' | 'done' | 'error';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function ToolVerificationPanel({ baseUrl, fetcher = fetch, api }: Props) {
  const [phase, setPhase] = useState<Phase>('idle');
  const [results, setResults] = useState<ToolResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleVerify() {
    setError(null);
    setResults([]);
    setPhase('running');
    try {
      const res = await api.verifyTools(baseUrl, fetcher);
      const raw = (res as Record<string, unknown>).tools as Array<Record<string, unknown>> | undefined;
      const mapped: ToolResult[] = (raw || []).map((t) => ({
        tool_name: String(t.tool_name ?? t.name ?? 'unknown'),
        status: String(t.status ?? 'unknown'),
        message: String(t.message ?? ''),
      }));
      setResults(mapped);
      setPhase('done');
    } catch (e) {
      setError(`验证失败：${e instanceof Error ? e.message : String(e)}`);
      setPhase('error');
    }
  }

  return (
    <div style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>工具验证</h2>
      <div style={{ color: '#666', fontSize: '0.75rem', marginBottom: '0.75rem' }}>检查工具链可用性并展示验证结果</div>

      {error && <div style={{ padding: '0.5rem', color: '#c44', marginBottom: '0.75rem' }}>{error}</div>}

      {phase === 'running' && (
        <div style={{ padding: '0.5rem', color: '#6b7280', fontSize: 13 }}>正在验证工具链...</div>
      )}

      {phase === 'done' && results.length === 0 && (
        <div style={{ padding: '0.5rem', color: '#888' }}>未返回任何工具结果。</div>
      )}

      {results.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.8rem' }}>验证结果</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {results.map((r, i) => (
              <div key={i} style={{ padding: '6px 8px', borderRadius: '4px', background: '#f9fafb', border: '1px solid #e5e7eb', fontSize: 12 }}>
                <div style={{ fontWeight: 600 }}>{r.tool_name}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 2 }}>
                  <span style={{ color: '#6b7280' }}>状态：</span>
                  <span style={{ color: r.status === 'ok' ? '#16a34a' : r.status === 'error' ? '#dc2626' : '#6b7280' }}>{r.status}</span>
                </div>
                {r.message && <div style={{ color: '#666', marginTop: 2 }}>消息：{r.message}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      <button type="button" onClick={handleVerify} style={{ padding: '6px 10px', borderRadius: '4px', border: '1px solid #bbb', background: '#f4f4f4', cursor: 'pointer' }}>
        验证工具链
      </button>

      <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#999', borderTop: '1px solid #eee', paddingTop: '0.5rem' }}>
        此面板仅验证工具链可用性，不提供危险操作。
      </div>
    </div>
  );
}
