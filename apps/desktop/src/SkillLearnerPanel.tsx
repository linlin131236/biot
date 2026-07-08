/**
 * SkillLearnerPanel — 技能学习器 (M162)。
 * 主动扫描失败记忆，检测模式，生成改进提案。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useState } from 'react';

interface Props {
  baseUrl: string;
  api: {
    autoScan: (b: string, k: string, f: Fetcher) => Promise<Record<string, unknown>>;
    recordFailure: (b: string, p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'executing' | 'done' | 'error';

interface PatternInfo {
  pattern_id?: string;
  category?: string;
  summary?: string;
  failure_count?: number;
  suggestion?: string;
}

interface ProposalInfo {
  proposal_id?: string;
  title_cn?: string;
  target_type?: string;
  status?: string;
  options?: string[];
}

interface ScanResult {
  keyword?: string;
  patterns_found?: number;
  proposals_generated?: number;
  total_failures_tracked?: number;
  patterns?: PatternInfo[];
  proposals?: ProposalInfo[];
  message?: string;
}

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

const VERDICT_COLORS: Record<string, string> = {
  draft: '#6b7280',
  approved: '#16a34a',
  rejected: '#dc2626',
  applied: '#2563eb',
};

export function SkillLearnerPanel({ baseUrl, api }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [keyword, setKeyword] = useState('');
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState('');

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError('');
    setKeyword('');
  }

  function handleAutoScan() {
    setError('');
    setPhase('executing');
    api.autoScan(baseUrl, keyword.trim(), window.fetch)
      .then((data) => {
        const r = data as Record<string, unknown>;
        const rawPatterns = Array.isArray(r.patterns) ? r.patterns : [];
        const rawProposals = Array.isArray(r.proposals) ? r.proposals : [];
        const patterns: PatternInfo[] = rawPatterns.map((p: Record<string, unknown>) => ({
          pattern_id: String(p.pattern_id ?? ''),
          category: String(p.category ?? ''),
          summary: String(p.summary ?? ''),
          failure_count: typeof p.failure_count === 'number' ? p.failure_count : 0,
          suggestion: String(p.suggestion ?? ''),
        }));
        const proposals: ProposalInfo[] = rawProposals.map((p: Record<string, unknown>) => ({
          proposal_id: String(p.proposal_id ?? ''),
          title_cn: String(p.title_cn ?? ''),
          target_type: String(p.target_type ?? ''),
          status: String(p.status ?? ''),
          options: Array.isArray(p.options) ? p.options.map((o: unknown) => String(o)) : [],
        }));
        setResult({
          keyword: String(r.keyword ?? keyword.trim()),
          patterns_found: typeof r.patterns_found === 'number' ? (r.patterns_found as number) : patterns.length,
          proposals_generated: typeof r.proposals_generated === 'number' ? (r.proposals_generated as number) : proposals.length,
          total_failures_tracked: typeof r.total_failures_tracked === 'number' ? (r.total_failures_tracked as number) : 0,
          patterns,
          proposals,
          message: typeof r.message === 'string' ? (r.message as string) : '',
        });
        setPhase('done');
      })
      .catch((e) => {
        setError(`自动扫描失败：${e instanceof Error ? e.message : String(e)}`);
        setPhase('error');
      });
  }

  function handleRecordFailure() {
    setError('');
    setPhase('executing');
    api.recordFailure(baseUrl, { failure_class: 'manual', failure_id: `manual_${Date.now()}`, description_cn: '用户手动记录失败' }, window.fetch)
      .then(() => {
        setResult((prev) => prev ? { ...prev, total_failures_tracked: (prev.total_failures_tracked ?? 0) + 1 } : prev);
        setPhase('done');
      })
      .catch((e) => {
        setError(`记录失败失败：${e instanceof Error ? e.message : String(e)}`);
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
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在扫描失败记忆...</div>;
  }

  if (phase === 'done' && result) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>扫描结果</h3>

        {result.message && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12, color: '#666', fontSize: 12 }}>
            {result.message}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '8px 12px', flex: 1 }}>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>模式发现</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{result.patterns_found ?? 0}</div>
          </div>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '8px 12px', flex: 1 }}>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>提案生成</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{result.proposals_generated ?? 0}</div>
          </div>
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '8px 12px', flex: 1 }}>
            <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>跟踪失败</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{result.total_failures_tracked ?? 0}</div>
          </div>
        </div>

        {result.patterns && result.patterns.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>检测到的模式</div>
            {result.patterns.map((p, i) => (
              <div key={p.pattern_id || i} style={{ padding: '6px 0', borderBottom: i < result.patterns!.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{p.category || '未知'}</span>
                  <span style={{ fontSize: 11, color: '#9ca3af' }}>×{p.failure_count ?? 0}</span>
                </div>
                <div style={{ fontSize: 12 }}>{p.summary || '—'}</div>
                {p.suggestion && <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>建议：{p.suggestion}</div>}
              </div>
            ))}
          </div>
        )}

        {result.proposals && result.proposals.length > 0 && (
          <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>改进提案</div>
            {result.proposals.map((p, i) => (
              <div key={p.proposal_id || i} style={{ padding: '6px 0', borderBottom: i < result.proposals!.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 3, background: VERDICT_COLORS[p.status || 'draft'] || '#6b7280', color: '#fff', fontWeight: 600 }}>{p.status || 'draft'}</span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{p.title_cn || '未命名提案'}</span>
                </div>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>目标类型：{p.target_type || 'unknown'}</div>
                {p.options && p.options.length > 0 && (
                  <div style={{ fontSize: 11, color: '#374151', marginTop: 4 }}>
                    <span style={{ fontWeight: 600 }}>选项：</span>
                    {p.options.map((opt, j) => (
                      <span key={j} style={{ display: 'inline-block', padding: '2px 8px', margin: '2px 4px 2px 0', borderRadius: 3, border: '1px solid #d1d5db', background: '#fff', fontSize: 11 }}>
                        {['A', 'B', 'C'][j] || String(j + 1)}. {opt}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>新建扫描</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>技能学习器</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        分析失败模式，提出改进建议。需用户审批后应用。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>关键词（可选）</label>
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
          placeholder="输入关键词筛选失败记忆"
        />
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button
          onClick={handleAutoScan}
          style={{ padding: '6px 16px', fontSize: 12, borderRadius: 3, border: '1px solid #2563eb', background: '#2563eb', color: '#fff', cursor: 'pointer' }}
        >
          自动扫描
        </button>
        <button
          onClick={handleRecordFailure}
          style={{ padding: '6px 16px', fontSize: 12, borderRadius: 3, border: '1px solid #d97706', background: '#fff', color: '#d97706', cursor: 'pointer' }}
        >
          手动记录失败
        </button>
      </div>
    </div>
  );
}
