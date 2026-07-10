/**
 * BuilderPanel — 构建执行引擎 (M160)。
 * 产生代码变更提案，需人工审批后应用。
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import { useState } from 'react';

interface Props {
  fetcher?: Fetcher;
  api: {
    executeTask: (payload: Record<string, unknown>, fetcher: Fetcher) => Promise<Record<string, unknown>>;
    fetchProposals: (fetcher: Fetcher) => Promise<Record<string, unknown>>;
  };
}

type Phase = 'form' | 'executing' | 'done' | 'error';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function BuilderPanel({ api, fetcher }: Props) {
  const [phase, setPhase] = useState<Phase>('form');
  const [taskId, setTaskId] = useState('');
  const [description, setDescription] = useState('');
  const [targetFiles, setTargetFiles] = useState('');
  const [workspace, setWorkspace] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  function handleReset() {
    setPhase('form');
    setResult(null);
    setError('');
    setTaskId('');
    setDescription('');
    setTargetFiles('');
    setWorkspace('');
  }

  function handleExecute() {
    if (!taskId.trim() || !description.trim() || !workspace.trim()) return;
    setError('');
    setPhase('executing');
    const payload: Record<string, unknown> = {
      task_id: taskId.trim(),
      description_cn: description.trim(),
      target_files: targetFiles.split('\n').map((s) => s.trim()).filter((s) => s.length > 0),
      workspace: workspace.trim(),
    };
    api.executeTask(payload, fetcher)
      .then((data) => {
        setResult(data);
        setPhase('done');
      })
      .catch((e) => {
        setError(`执行构建失败：${e instanceof Error ? e.message : String(e)}`);
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
    return <div style={{ padding: '0.75rem', color: '#6b7280', fontSize: 13 }}>正在执行构建任务...</div>;
  }

  if (phase === 'done' && result) {
    const output = (result.output as Record<string, unknown>) || {};
    const codeChanges = output.code_changes;
    const tests = output.tests;
    const evidenceRefs = output.evidence_refs;
    const sourceRefs = output.source_refs;
    const proposals = result.proposals;

    return (
      <div style={{ padding: '12px 16px', fontSize: 13 }}>
        <h3 style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600 }}>构建结果</h3>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>任务 ID：{String(result.task_id ?? '')}</div>
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>代码变更</div>
          {codeChanges === undefined || codeChanges === null ? (
            <div style={{ color: '#9ca3af' }}>无</div>
          ) : (
            <pre style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 3, padding: '8px 10px', fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0 }}>
              {typeof codeChanges === 'string' ? codeChanges : JSON.stringify(codeChanges, null, 2)}
            </pre>
          )}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>测试命令</div>
          {tests === undefined || tests === null ? (
            <div style={{ color: '#9ca3af' }}>无</div>
          ) : (
            <div style={{ whiteSpace: 'pre-wrap' }}>
              {typeof tests === 'string' ? tests : JSON.stringify(tests, null, 2)}
            </div>
          )}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>证据引用</div>
          {evidenceRefs === undefined || evidenceRefs === null ? (
            <div style={{ color: '#9ca3af' }}>无</div>
          ) : Array.isArray(evidenceRefs) ? (
            evidenceRefs.map((ref: unknown, i: number) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < evidenceRefs.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {typeof ref === 'string' ? ref : JSON.stringify(ref)}
              </div>
            ))
          ) : (
            <div style={{ whiteSpace: 'pre-wrap' }}>{typeof evidenceRefs === 'string' ? evidenceRefs : JSON.stringify(evidenceRefs, null, 2)}</div>
          )}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>来源引用</div>
          {sourceRefs === undefined || sourceRefs === null ? (
            <div style={{ color: '#9ca3af' }}>无</div>
          ) : Array.isArray(sourceRefs) ? (
            sourceRefs.map((ref: unknown, i: number) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < sourceRefs.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {typeof ref === 'string' ? ref : JSON.stringify(ref)}
              </div>
            ))
          ) : (
            <div style={{ whiteSpace: 'pre-wrap' }}>{typeof sourceRefs === 'string' ? sourceRefs : JSON.stringify(sourceRefs, null, 2)}</div>
          )}
        </div>

        <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>提案状态</div>
          {proposals === undefined || proposals === null ? (
            <div style={{ color: '#9ca3af' }}>无提案</div>
          ) : Array.isArray(proposals) ? (
            proposals.map((p: unknown, i: number) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: i < proposals.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
                {typeof p === 'string' ? p : JSON.stringify(p)}
              </div>
            ))
          ) : (
            <div style={{ whiteSpace: 'pre-wrap' }}>{typeof proposals === 'string' ? proposals : JSON.stringify(proposals, null, 2)}</div>
          )}
        </div>

        <button onClick={handleReset} style={{ padding: '4px 12px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', background: '#fff', cursor: 'pointer' }}>新建任务</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 16px', fontSize: 13 }}>
      <h2 style={{ margin: '0 0 0.25rem', fontSize: '1rem' }}>构建引擎</h2>
      <div style={{ fontSize: '0.7rem', color: '#999', marginBottom: '0.75rem' }}>
        产生代码变更提案，需人工审批后应用。
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>任务 ID</label>
        <input
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box' }}
          placeholder="输入任务 ID"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>描述</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="输入构建任务描述"
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>目标文件</label>
        <textarea
          value={targetFiles}
          onChange={(e) => setTargetFiles(e.target.value)}
          rows={3}
          style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ccc', boxSizing: 'border-box', resize: 'vertical' }}
          placeholder="每行一个目标文件路径"
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
        onClick={handleExecute}
        disabled={!taskId.trim() || !description.trim() || !workspace.trim()}
        style={{
          padding: '6px 16px',
          fontSize: 12,
          borderRadius: 3,
          border: '1px solid #16a34a',
          background: (!taskId.trim() || !description.trim() || !workspace.trim()) ? '#e5e7eb' : '#16a34a',
          color: (!taskId.trim() || !description.trim() || !workspace.trim()) ? '#9ca3af' : '#fff',
          cursor: (!taskId.trim() || !description.trim() || !workspace.trim()) ? 'not-allowed' : 'pointer',
        }}
      >
        执行构建
      </button>
    </div>
  );
}
