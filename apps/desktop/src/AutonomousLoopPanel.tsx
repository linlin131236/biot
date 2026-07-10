/**
 * AutonomousLoopPanel — 自主循环 (M170)。
 * 启动/展示自主循环执行结果。
 * 纯前端控制，不访问 ipcRenderer/process/require。
 */
import { useEffect, useState } from 'react';

interface Props {
  fetcher?: Fetcher;
  api: {
    runAutonomousLoop: (payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'running' | 'done' | 'error';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface LoopResult {
  status?: string;
  rounds_completed?: number;
  verdict?: string;
  trace?: Array<Record<string, unknown>>;
  message?: string;
}

export function AutonomousLoopPanel({ fetcher, api }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [maxRounds, setMaxRounds] = useState('5');
  const [result, setResult] = useState<LoopResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setError(null);
    setResult(null);
    setPhase('running');
    try {
      const res = await api.runAutonomousLoop({
        max_rounds: Math.min(Number(maxRounds) || 5, 100),
      }, fetcher);
      const r = res as Record<string, unknown>;
      setResult({
        status: String(r.status ?? 'completed'),
        rounds_completed: typeof r.rounds_completed === 'number' ? (r.rounds_completed as number) : 0,
        verdict: String(r.verdict ?? 'approved'),
        trace: Array.isArray(r.trace) ? (r.trace as Array<Record<string, unknown>>) : [],
        message: typeof r.message === 'string' ? (r.message as string) : '',
      });
      setPhase('done');
    } catch (e) {
      setError(`启动自主循环失败：${e instanceof Error ? e.message : String(e)}`);
      setPhase('error');
    }
  }

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError(null);
    setMaxRounds('5');
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
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>自主循环执行中...</div>;
  }

  if (phase === 'done' && result) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>循环结果</h3>

        {result.message && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12, color: '#666', fontSize: 12 }}>
            {result.message}
          </div>
        )}

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>状态：{result.status}</div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>完成轮次：{result.rounds_completed}</div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>裁决：{result.verdict}</div>
        </div>

        {result.trace && result.trace.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>执行轨迹</div>
            {result.trace.map((step, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < result.trace!.length - 1 ? '1px solid #f3f4f6' : 'none', fontSize: 12 }}>
                {typeof step === 'string' ? step : JSON.stringify(step)}
              </div>
            ))}
          </div>
        )}

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>重新启动</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>自主循环</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        启动端到端自主执行循环。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>最大轮次</label>
        <input
          type="number"
          value={maxRounds}
          onChange={(e) => setMaxRounds(e.target.value)}
          min={1}
          max={100}
          aria-label="最大轮次"
          style={{ width: '8rem', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
        />
      </div>

      <button
        onClick={handleRun}
        disabled={Number(maxRounds) < 1}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #16a34a',
          background: Number(maxRounds) < 1 ? '#e5e7eb' : '#16a34a',
          color: Number(maxRounds) < 1 ? '#9ca3af' : '#fff',
          cursor: Number(maxRounds) < 1 ? 'not-allowed' : 'pointer',
        }}
      >
        启动自主循环
      </button>
    </div>
  );
}
