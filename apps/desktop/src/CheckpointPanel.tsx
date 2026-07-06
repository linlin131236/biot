/**
 * CheckpointPanel — 安全检查点面板。
 * M40: 创建/加载/审计展示检查点，不自动回滚写文件。
 * 不直接访问 fs/shell/process/ipcRenderer。
 * 所有文案中文。
 */
import { useState } from 'react';
import type { Checkpoint } from '@bolt/shared/autonomy';

interface CheckpointPanelApi {
  createCheckpoint: (baseUrl: string, payload: Record<string, unknown>) => Promise<Checkpoint>;
  loadCheckpoint: (baseUrl: string, cpId: string) => Promise<Checkpoint | null>;
}

interface CheckpointPanelProps {
  runId: string | null;
  goalId: string | null;
  api: CheckpointPanelApi;
  baseUrl?: string;
}

export function CheckpointPanel({ runId, goalId, api, baseUrl = 'http://core' }: CheckpointPanelProps) {
  const [cp, setCp] = useState<Checkpoint | null>(null);
  const [cpInput, setCpInput] = useState('');
  const [loadResult, setLoadResult] = useState<Checkpoint | null>(null);
  const [loadAttempted, setLoadAttempted] = useState(false);
  const [error, setError] = useState('');
  const canCreate = !!runId && !!goalId;

  async function handleCreate() {
    if (!runId || !goalId) return;
    setError(''); try {
      const result = await api.createCheckpoint(baseUrl, { run_id: runId, goal_id: goalId });
      setCp(result);
    } catch { setError('检查点创建失败'); }
  }

  async function handleLoad() {
    setError(''); if (!cpInput.trim()) return;
    setLoadAttempted(true);
    try { const result = await api.loadCheckpoint(baseUrl, cpInput.trim()); setLoadResult(result); }
    catch { setError('检查点加载失败'); }
  }

  return <section className="checkpointPanel">
    <h2>安全检查点</h2>
    <button type="button" disabled={!canCreate} onClick={handleCreate}>创建检查点</button>
    {!canCreate && !goalId ? <span>暂无目标，无法创建检查点</span> : null}
    {error ? <span className="error">{error}</span> : null}
    {cp ? <div className="cpSummary"><span>检查点 {cp.id}</span><span>运行 {cp.run_id}</span><span>目标 {cp.goal_id}</span><span>{cp.changed_files.length} 个变更文件</span><span>{cp.pending_permissions.length} 个待审批</span></div> : null}
    <input aria-label="检查点 ID" value={cpInput} onChange={e => { setCpInput(e.target.value); setLoadAttempted(false); }} />
    <button type="button" disabled={!cpInput.trim()} onClick={handleLoad}>加载检查点</button>
    {loadAttempted && loadResult === null ? <span>未找到检查点</span> : null}
    {loadResult ? <div className="cpSummary"><span>检查点 {loadResult.id}</span><span>运行 {loadResult.run_id}</span><span>目标 {loadResult.goal_id}</span><span>{loadResult.changed_files.length} 个变更文件</span><span>{loadResult.pending_permissions.length} 个待审批</span></div> : null}
  </section>;
}
