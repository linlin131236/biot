/**
 * TestRunnerPanel — 安全测试运行器 (M157)。
 * 只运行白名单测试命令，显示运行前确认、运行中/成功/失败状态、脱敏输出。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface TestOption {
  test_id: string;
  description: string;
  timeout_seconds: number;
}

interface TestRunResult {
  test_id: string;
  status: string;
  exit_code: number | null;
  summary: string;
  output_snippet: string;
  evidence_hash: string;
}

interface Props {
  baseUrl: string;
  api: {
    fetchAvailableTests: (baseUrl: string) => Promise<Record<string, unknown>>;
    runTest: (baseUrl: string, testId: string, extraArgs?: string[]) => Promise<Record<string, unknown>>;
    fetchTestHistory: (baseUrl: string) => Promise<Record<string, unknown>>;
  };
}

type RunState = 'idle' | 'confirming' | 'running' | 'done';

export function TestRunnerPanel({ baseUrl, api }: Props) {
  const [tests, setTests] = useState<TestOption[]>([]);
  const [selectedTest, setSelectedTest] = useState<string>('');
  const [runState, setRunState] = useState<RunState>('idle');
  const [result, setResult] = useState<TestRunResult | null>(null);
  const [history, setHistory] = useState<TestRunResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.fetchAvailableTests(baseUrl)
      .then((data) => {
        if (cancelled) return;
        const available = (data as Record<string, unknown>).available_tests as Record<string, { description: string; timeout_seconds: number }> | undefined;
        if (available) {
          setTests(Object.entries(available).map(([test_id, info]) => ({
            test_id,
            description: info.description,
            timeout_seconds: info.timeout_seconds,
          })));
        }
      })
      .catch((e) => {
        if (!cancelled) setError(`加载失败：${e instanceof Error ? e.message : String(e)}`);
      });
    return () => { cancelled = true; };
  }, [baseUrl, api]);

  useEffect(() => {
    let cancelled = false;
    api.fetchTestHistory(baseUrl)
      .then((data) => {
        if (cancelled) return;
        const hist = (data as Record<string, unknown>).history as TestRunResult[] | undefined;
        if (hist) setHistory(hist);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [baseUrl, api, runState]);

  function handleRun() {
    if (!selectedTest) return;
    setRunState('confirming');
    setResult(null);
    setError(null);
  }

  function confirmRun() {
    setRunState('running');
    api.runTest(baseUrl, selectedTest)
      .then((data) => {
        const res = (data as Record<string, unknown>).result as TestRunResult;
        setResult(res);
        setRunState('done');
      })
      .catch((e) => {
        setError(`运行失败：${e instanceof Error ? e.message : String(e)}`);
        setRunState('idle');
      });
  }

  function cancelRun() {
    setRunState('idle');
    setResult(null);
  }

  function statusLabel(status: string): string {
    const map: Record<string, string> = {
      passed: '通过', failed: '失败', timed_out: '超时',
      blocked: '已阻止', error: '错误', running: '运行中',
    };
    return map[status] || status;
  }

  function statusColor(status: string): string {
    if (status === 'passed' || status === 'running') return '#16a34a';
    if (status === 'failed' || status === 'timed_out' || status === 'error') return '#dc2626';
    if (status === 'blocked') return '#d97706';
    return '#6b7280';
  }

  if (error) {
    return <div style={{ padding: '1rem', color: '#c44' }}>{error}</div>;
  }

  return (
    <div style={{ padding: '0.75rem', fontSize: '0.85rem' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>安全测试运行器</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.5rem' }}>
        仅白名单命令可运行，不自动修复失败。
      </div>

      {/* Test selection */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#666', marginRight: 8 }}>选择测试：</label>
        <select
          value={selectedTest}
          onChange={(e) => { setSelectedTest(e.target.value); setRunState('idle'); setResult(null); }}
          style={{ padding: '4px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc' }}
        >
          <option value="">-- 选择 --</option>
          {tests.map((t) => (
            <option key={t.test_id} value={t.test_id}>{t.description}</option>
          ))}
        </select>
        {selectedTest && runState === 'idle' && (
          <button onClick={handleRun} style={{ marginLeft: 8, padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #16a34a', background: '#16a34a', color: '#fff', cursor: 'pointer' }}>运行</button>
        )}
      </div>

      {/* Confirmation dialog */}
      {runState === 'confirming' && selectedTest && (
        <div style={{ background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 4, padding: 10, marginBottom: 12 }}>
          <div style={{ fontSize: 13, marginBottom: 8, fontWeight: 600 }}>确认运行测试</div>
          <div style={{ fontSize: 12, color: '#92400e', marginBottom: 4 }}>
            测试：{tests.find(t => t.test_id === selectedTest)?.description}
          </div>
          <div style={{ fontSize: 12, color: '#92400e', marginBottom: 8 }}>
            超时：{tests.find(t => t.test_id === selectedTest)?.timeout_seconds}s
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={confirmRun} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #16a34a', background: '#16a34a', color: '#fff', cursor: 'pointer' }}>确认运行</button>
            <button onClick={cancelRun} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>取消</button>
          </div>
        </div>
      )}

      {/* Running state */}
      {runState === 'running' && (
        <div style={{ padding: '8px 0', color: '#16a34a', fontSize: 13 }}>运行中...</div>
      )}

      {/* Result */}
      {runState === 'done' && result && (
        <div style={{ background: result.status === 'passed' ? '#f0fdf4' : '#fef2f2', border: `1px solid ${statusColor(result.status)}`, borderRadius: 4, padding: 10, marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontWeight: 600, color: statusColor(result.status) }}>{statusLabel(result.status)}</span>
            <span style={{ fontSize: 11, color: '#999' }}>{result.summary}</span>
          </div>
          {result.output_snippet && (
            <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: '8px 10px', borderRadius: 3, fontSize: 11, maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {result.output_snippet}
            </pre>
          )}
          <div style={{ fontSize: 10, color: '#999', marginTop: 4 }}>
            证据哈希：{result.evidence_hash}
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <h3 style={{ margin: '0 0 8px', fontSize: 12, fontWeight: 600, color: '#6b7280' }}>运行历史</h3>
          <div style={{ maxHeight: 150, overflowY: 'auto' }}>
            {history.slice(0, 10).map((h, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', fontSize: 11, borderBottom: '1px solid #f3f4f6' }}>
                <span>{h.test_id}</span>
                <span style={{ color: statusColor(h.status) }}>{statusLabel(h.status)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
