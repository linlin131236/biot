/**
 * GoalConsole — 长任务驾驶舱。创建/启动/暂停/恢复/停止长任务。
 * M38: 发现未完成长任务、时间线/证据面板、失败诊断。
 * 不直接访问 fs/shell/process/ipcRenderer。
 * 所有文案中文。
 */

import { useEffect, useState } from 'react';
import type { AgentLoopResult } from '@bolt/shared';
import type { Goal, GoalStatus, TimelineEvent, GoalEvidence } from '@bolt/shared/autonomy';

interface GoalConsoleApi {
  createGoal: (baseUrl: string, payload: Record<string, unknown>) => Promise<Goal>;
  startRun: (baseUrl: string, goal: string, workspace: string) => Promise<{ id: string }>;
  runAgentLoop: (baseUrl: string, runId: string, maxSteps: number) => Promise<AgentLoopResult>;
  pauseGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  resumeGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  clearGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  getGoal: (baseUrl: string, goalId: string) => Promise<Goal | null>;
  fetchGoalEvidence: (baseUrl: string, goalId: string) => Promise<GoalEvidence[]>;
  fetchRunTimeline: (baseUrl: string, runId: string) => Promise<TimelineEvent[]>;
}

const STATUS_LABEL: Record<GoalStatus | 'rejected', string> = {
  pending: '未开始', running: '运行中', paused: '已暂停',
  stopped: '已停止', completed: '已完成', failed: '失败', rejected: '已拒绝',
};

function loopStatusToGoalStatus(loopStatus: AgentLoopResult['status'], steps: number, maxSteps: number): GoalStatus {
  if (steps >= maxSteps && maxSteps > 0) return 'stopped';
  if (loopStatus === 'pending_permission' || loopStatus === 'approved') return 'paused';
  if (loopStatus === 'failed') return 'failed';
  if (loopStatus === 'rejected' || loopStatus === 'denied') return 'rejected';
  return 'running';
}

function nextSuggestion(status: GoalStatus | null, isMaxed: boolean): string | null {
  if (status === 'failed') return '建议：检查错误日志后重新创建任务';
  if (status === 'stopped' && isMaxed) return '建议：增加最大步数或缩小任务范围';
  if (status === 'paused') return '建议：批准待审批权限后恢复任务';
  return null;
}

interface GoalConsoleProps {
  workspacePath: string;
  goal: Goal | null;
  api: GoalConsoleApi;
  baseUrl?: string;
  maxSteps?: number;
  unfinishedGoals?: Goal[];
}

export function GoalConsole({ workspacePath, goal, api, baseUrl = 'http://core', maxSteps = 10, unfinishedGoals }: GoalConsoleProps) {
  const [objective, setObjective] = useState('');
  const [error, setError] = useState('');
  const [currentGoal, setCurrentGoal] = useState<Goal | null>(goal);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [loopStepCount, setLoopStepCount] = useState(0);
  const [timeline, setTimeline] = useState<TimelineEvent[] | null>(null);
  const [evidence, setEvidence] = useState<GoalEvidence[] | null>(null);

  const hasWorkspace = workspacePath.length > 0;
  const hasObjective = objective.trim().length >= 5;
  const canStart = hasWorkspace && hasObjective;
  const displayGoal = currentGoal || goal || (unfinishedGoals && unfinishedGoals.length > 0 ? unfinishedGoals[0] : null);

  // Fetch evidence when goal is active (doesn't need runId)
  useEffect(() => {
    const g = currentGoal || goal || (unfinishedGoals?.length ? unfinishedGoals[0] : null);
    if (!g) { setEvidence(null); return; }
    let active = true;
    api.fetchGoalEvidence(baseUrl, g.id).then(e => { if (active) setEvidence(e); }).catch(() => {});
    return () => { active = false; };
  }, [baseUrl, currentGoal?.id, goal?.id, unfinishedGoals, api]);

  // Fetch timeline only when both goal + runId exist
  useEffect(() => {
    if (!currentRunId) { setTimeline(null); return; }
    let active = true;
    api.fetchRunTimeline(baseUrl, currentRunId).then(t => { if (active) setTimeline(t); }).catch(() => {});
    return () => { active = false; };
  }, [baseUrl, currentRunId, api]);

  async function handleStart() {
    setError('');
    if (!objective.trim()) { setError('请输入任务目标'); return; }
    if (objective.trim().length < 5) { setError('任务目标至少5个字'); return; }
    try {
      const g = await api.createGoal(baseUrl, { objective: objective.trim(), criteria: ['任务完成'], max_steps: maxSteps, workspace: workspacePath });
      setCurrentGoal(g);
      const run = await api.startRun(baseUrl, objective.trim(), workspacePath);
      setCurrentRunId(run.id);
      const loopResult = await api.runAgentLoop(baseUrl, run.id, maxSteps);
      setLoopStepCount(loopResult.steps);
      const derivedStatus = loopStatusToGoalStatus(loopResult.status, loopResult.steps, maxSteps);
      setCurrentGoal(prev => prev ? { ...prev, status: derivedStatus, step_count: loopResult.steps } : prev);
      if (loopResult.error) { setError(loopResult.error); }
    } catch (e) { setError(String(e)); }
  }

  async function handlePause() {
    if (!currentGoal) return;
    try { const g = await api.pauseGoal(baseUrl, currentGoal.id); setCurrentGoal(g); } catch (e) { setError(String(e)); }
  }

  /** Resume from unfinished-banner: need startRun for new runId if cold-start */
  async function handleResumeFromBanner() {
    const target = displayGoal;
    if (!target) return;
    setCurrentGoal(target);
    try {
      const g = await api.resumeGoal(baseUrl, target.id);
      setCurrentGoal(g);
      if (g.status !== 'running') {
        setError('恢复被阻止，请检查工作区冲突');
        return;
      }
      // Cold-start: no currentRunId → start a new run to get one
      let runId = currentRunId;
      if (!runId) {
        const run = await api.startRun(baseUrl, target.objective, workspacePath);
        runId = run.id;
        setCurrentRunId(runId);
      }
      const loopResult = await api.runAgentLoop(baseUrl, runId, maxSteps);
      setLoopStepCount(loopResult.steps);
      const derivedStatus = loopStatusToGoalStatus(loopResult.status, loopResult.steps, maxSteps);
      setCurrentGoal(prev => prev ? { ...prev, status: derivedStatus, step_count: loopResult.steps } : prev);
      if (loopResult.error) { setError(loopResult.error); }
    } catch (e) { setError(String(e)); }
  }

  async function handleResume() {
    if (!currentGoal) return;
    try {
      const g = await api.resumeGoal(baseUrl, currentGoal.id);
      setCurrentGoal(g);
      if (g.status !== 'running') {
        setError('恢复被阻止，请检查工作区冲突');
        return;
      }
      if (currentRunId) {
        const loopResult = await api.runAgentLoop(baseUrl, currentRunId, maxSteps);
        setLoopStepCount(loopResult.steps);
        const derivedStatus = loopStatusToGoalStatus(loopResult.status, loopResult.steps, maxSteps);
        setCurrentGoal(prev => prev ? { ...prev, status: derivedStatus, step_count: loopResult.steps } : prev);
        if (loopResult.error) { setError(loopResult.error); }
      }
    } catch (e) { setError(String(e)); }
  }

  async function handleStop() {
    if (!currentGoal) return;
    try { const g = await api.clearGoal(baseUrl, currentGoal.id); setCurrentGoal(g); setCurrentRunId(null); } catch (e) { setError(String(e)); }
  }

  const status = displayGoal?.status ?? null;
  const stepCount = displayGoal?.step_count ?? loopStepCount;
  const isMaxed = stepCount >= maxSteps && maxSteps > 0;
  const suggestion = nextSuggestion(status, isMaxed);
  const showUnfinishedBanner = !!unfinishedGoals && unfinishedGoals.length > 0 && !currentGoal && !goal;

  function statusLine() {
    return <>
      <strong>{status ? STATUS_LABEL[status as GoalStatus | 'rejected'] ?? status : ''}</strong>
      {status === 'paused' ? <span>等待人工批准</span> : null}
      {isMaxed && (status === 'stopped' || status === 'paused') ? <span>已达到最大步数</span> : null}
      <span>{stepCount} / {maxSteps}</span>
    </>;
  }

  return <section className="goalConsole">
    <h2>长任务驾驶舱</h2>
    {showUnfinishedBanner ? <div className="unfinishedBanner">
      <span>发现未完成长任务</span>
      <div className="unfinishedGoalInfo">
        <span>{displayGoal?.id}</span>
        <span>{displayGoal?.objective}</span>
        {statusLine()}
      </div>
      <button type="button" disabled={!hasWorkspace} onClick={handleResumeFromBanner}>恢复任务</button>
      {suggestion ? <span className="suggestion">{suggestion}</span> : null}
    </div> : !displayGoal ? <div className="goalCreate">
      <label>长任务目标 <input aria-label="长任务目标" value={objective} onChange={e => setObjective(e.target.value)} /></label>
      <button type="button" disabled={!canStart} onClick={handleStart}>开始长任务</button>
      {error ? <span className="error">{error}</span> : null}
    </div> : <div className="goalControl">
      <div className="statusBar">
        {statusLine()}
        <span>{displayGoal.objective}</span>
      </div>
      {suggestion ? <span className="suggestion">{suggestion}</span> : null}
      <div className="actions">
        {status === 'running' ? <button type="button" onClick={handlePause}>暂停任务</button> : null}
        {status === 'paused' ? <button type="button" onClick={handleResume}>恢复任务</button> : null}
        {status === 'running' || status === 'paused' ? <button type="button" onClick={handleStop}>停止任务</button> : null}
      </div>
      {error ? <span className="error">{error}</span> : null}
    </div>}
    <div className="goalDetails">
      {timeline !== null ? <div className="timeline">
        {timeline.length === 0 ? <span>暂无长任务记录</span> : <>
          <span>{timeline.length} 条记录</span>
          <div className="timelineRecent">
            {timeline.slice(-5).map((e, i) => <div key={i} className="timelineEvent">
              <span>{e.type}</span>
              <span>{e.sequence}</span>
            </div>)}
          </div>
        </>}
      </div> : null}
      {evidence !== null ? <div className="evidence">
        {evidence.length === 0 ? <span>暂无证据</span> : <>
          <span>{evidence.length} 条证据</span>
          {evidence[0]?.summary ? <span>{evidence[0].summary}</span> : null}
        </>}
      </div> : null}
    </div>
  </section>;
}
