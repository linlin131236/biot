/**
 * ResearcherPanel — 只读研究员执行引擎 (M159)。
 * 创建研究摘要、执行数据源查询并展示中文研究结果。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useEffect, useState } from 'react';

interface Brief {
  brief_id: string;
  title: string;
  question: string;
  scope: string;
  status: string;
}

interface ResearchResult {
  brief_id: string;
  summary_cn: string;
  principles_cn: string[];
  risks_cn: string[];
  source_refs: Array<Record<string, unknown>>;
}

interface Props {
  baseUrl: string;
  fetcher?: Fetcher;
  api: {
    createBrief: (baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    executeResearch: (baseUrl: string, briefId: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchScopes: (baseUrl: string, fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'creating' | 'brief' | 'executing' | 'done' | 'error';

const SCOPES = [
  { value: 'project_docs', label: '项目文档' },
  { value: 'bincloud_refs', label: 'BinCloud 参考资料' },
  { value: 'code_map', label: '代码地图' },
  { value: 'decision_memory', label: '决策记忆' },
  { value: 'failure_memory', label: '失败记忆' },
];

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function ResearcherPanel({ baseUrl, api, fetcher = fetch }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [title, setTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [scope, setScope] = useState('');
  const [brief, setBrief] = useState<Brief | null>(null);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState('');
  const [scopes, setScopes] = useState<Array<{ value: string; label: string }>>(SCOPES);

  useEffect(() => {
    let cancelled = false;
    api.fetchScopes(baseUrl, fetcher)
      .then((data) => {
        if (cancelled) return;
        const raw = (data as Record<string, unknown>).scopes as Array<Record<string, unknown>> | undefined;
        if (raw && raw.length > 0) {
          setScopes(raw.map((s) => ({ value: String(s.value ?? s.id ?? ''), label: String(s.label ?? s.name ?? '') })));
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [baseUrl, api]);

  function handleCreateBrief() {
    if (!title.trim() || !question.trim() || !scope) return;
    setError('');
    setPhase('creating');
    api.createBrief(baseUrl, { title: title.trim(), question: question.trim(), scope }, fetcher)
      .then((data) => {
        const b = data as Record<string, unknown>;
        const briefRecord: Brief = {
          brief_id: String(b.brief_id ?? b.id ?? ''),
          title: String(b.title ?? title.trim()),
          question: String(b.question ?? question.trim()),
          scope: String(b.scope ?? scope),
          status: String(b.status ?? 'created'),
        };
        setBrief(briefRecord);
        setPhase('brief');
      })
      .catch((e) => {
        setError(`创建摘要失败：${e instanceof Error ? e.message : String(e)}`);
        setPhase('form');
      });
  }

  function handleExecute() {
    if (!brief?.brief_id) return;
    setError('');
    setPhase('executing');
    api.executeResearch(baseUrl, brief.brief_id, fetcher)
      .then((data) => {
        const r = data as Record<string, unknown>;
        const rawRefs = r.source_refs as Array<Record<string, unknown>> | undefined;
        setResult({
          brief_id: String(r.brief_id ?? brief.brief_id),
          summary_cn: String(r.summary_cn ?? ''),
          principles_cn: Array.isArray(r.principles_cn) ? r.principles_cn.map((x) => String(x)) : [],
          risks_cn: Array.isArray(r.risks_cn) ? r.risks_cn.map((x) => String(x)) : [],
          source_refs: rawRefs ?? [],
        });
        setPhase('done');
      })
      .catch((e) => {
        setError(`执行研究失败：${e instanceof Error ? e.message : String(e)}`);
        setPhase('brief');
      });
  }

  function handleReset() {
    setPhase('form');
    setBrief(null);
    setResult(null);
    setError('');
    setTitle('');
    setQuestion('');
    setScope('');
  }

  if (error) {
    return (
      <div style={{ padding: '1rem', color: '#c44' }}>
        {error}
        <button onClick={handleReset} style={{ marginLeft: 12, padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>重试</button>
      </div>
    );
  }

  if (phase === 'creating') {
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在创建研究摘要...</div>;
  }

  if (phase === 'executing') {
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在执行研究查询...</div>;
  }

  if (phase === 'done' && result) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>研究结果</h3>
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>摘要 ID：{result.brief_id}</div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>研究摘要</div>
          <div style={{ whiteSpace: 'pre-wrap' }}>{result.summary_cn || '无内容'}</div>
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>核心原则</div>
          {result.principles_cn.length === 0 && <div style={{ color: '#9ca3af' }}>无</div>}
          {result.principles_cn.map((item, i) => (
            <div key={i} style={{ padding: '4px 0', borderBottom: i < result.principles_cn.length - 1 ? '1px solid #f3f4f6' : 'none' }}>{item}</div>
          ))}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>风险</div>
          {result.risks_cn.length === 0 && <div style={{ color: '#9ca3af' }}>无</div>}
          {result.risks_cn.map((item, i) => (
            <div key={i} style={{ padding: '4px 0', color: '#92400e', borderBottom: i < result.risks_cn.length - 1 ? '1px solid #f3f4f6' : 'none' }}>{item}</div>
          ))}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>来源引用</div>
          {result.source_refs.length === 0 && <div style={{ color: '#9ca3af' }}>无</div>}
          {result.source_refs.map((ref, i) => {
            const url = typeof ref.url === 'string' ? ref.url : '';
            return (
              <div key={i} style={{ padding: '4px 0', fontSize: 12, borderBottom: i < result.source_refs.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {String(ref.title ?? ref.name ?? `来源 ${i + 1}`)}
                {url ? <span style={{ color: '#6b7280', marginLeft: 8 }}>{url}</span> : null}
              </div>
            );
          })}
        </div>

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>新建研究</button>
      </div>
    );
  }

  if (phase === 'brief' && brief) {
    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>研究摘要</h3>
        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>摘要 ID：{brief.brief_id}</div>
          <div style={{ fontWeight: 600 }}>{brief.title}</div>
          <div style={{ marginTop: 4, fontSize: 12 }}>{brief.question}</div>
          <div style={{ marginTop: 4, fontSize: 12, color: '#6b7280' }}>范围：{brief.scope}</div>
        </div>
        <button onClick={handleExecute} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #16a34a', background: '#16a34a', color: '#fff', cursor: 'pointer' }}>执行研究</button>
        <button onClick={handleReset} style={{ marginLeft: 8, padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>取消</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>研究员</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        只读研究，不修改文件。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>标题</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
          placeholder="输入研究标题"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>研究问题</label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="输入研究问题"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>范围</label>
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
        >
          <option value="">-- 选择范围 --</option>
          {scopes.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </div>

      <button
        onClick={handleCreateBrief}
        disabled={!title.trim() || !question.trim() || !scope}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #16a34a',
          background: (!title.trim() || !question.trim() || !scope) ? '#e5e7eb' : '#16a34a',
          color: (!title.trim() || !question.trim() || !scope) ? '#9ca3af' : '#fff',
          cursor: (!title.trim() || !question.trim() || !scope) ? 'not-allowed' : 'pointer',
        }}
      >
        创建摘要
      </button>
    </div>
  );
}
