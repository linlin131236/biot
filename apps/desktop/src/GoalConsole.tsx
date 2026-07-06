/**
 * GoalConsole — 长任务驾驶舱。创建/启动/暂停/恢复/停止长任务。
 * 不直接访问 fs/shell/process/ipcRenderer。
 * 所有文案中文。
 *
 * 行为闭环：
 * - handleStart: createGoal → startRun → runAgentLoop → 用返回值驱动 UI 状态
 * - handlePause: pauseGoal（后端 goal runner 会检查 goal 状态暂停 loop）
 * - handleResume: resumeGoal（后端恢复 loop）
 * - handleStop:  clearGoal（后端停止 loop）
 */

import { useState } from 'react';
import type { AgentLoopResult } from '@bolt/shared';
import type { Goal, GoalStatus } from '@bolt/shared/autonomy';

interface GoalConsoleApi {
  createGoal: (baseUrl: string, payload: Record<string, unknown>) => Promise<Goal>;
  startRun: (baseUrl: string, goal: string, workspace: string) => Promise<{ id: string }>;
  runAgentLoop: (baseUrl: string, runId: string, maxSteps: number) => Promise<AgentLoopResult>;
  pauseGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  resumeGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  clearGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  getGoal: (baseUrl: string, goalId: string) => Promise<Goal>;
  fetchGoalEvidence: (baseUrl: string, goalId: string) => Promise<unknown[]>;
}

const STATUS_LABEL: Record<GoalStatus | 'rejected', string> = {
  pending: '未开始',
  running: '运行中',
  paused: '已暂停',
  stopped: '已停止',
  completed: '已完成',
  failed: '失败',
  rejected: '已拒绝',
};

/** Map AgentLoopResult.status to a GoalStatus for UI display. */
function loopStatusToGoalStatus(loopStatus: AgentLoopResult['status'], steps: number, maxSteps: number): GoalStatus {
  // Max steps reached → stopped regardless of loop status
  if (steps >= maxSteps && maxSteps > 0) return 'stopped';
  if (loopStatus === 'pending_permission' || loopStatus === 'approved') return 'paused';
  if (loopStatus === 'failed') return 'failed';
  if (loopStatus === 'rejected' || loopStatus === 'denied') return 'rejected';
  return 'running';
}

interface GoalConsoleProps {
  workspacePath: string;
  goal: Goal | null;
  api: GoalConsoleApi;
  baseUrl?: string;
  maxSteps?: number;
}

export function GoalConsole({ workspacePath, goal, api, baseUrl = 'http://core', maxSteps = 10 }: GoalConsoleProps) {
  const [objective, setObjective] = useState('');
  const [error, setError] = useState('');
  const [currentGoal, setCurrentGoal] = useState<Goal | null>(goal);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [loopStepCount, setLoopStepCount] = useState(0);

  const hasWorkspace = workspacePath.length > 0;
  const hasObjective = objective.trim().length >= 5;
  const canStart = hasWorkspace && hasObjective;

  async function handleStart() {
    setError('');
    if (!objective.trim()) { setError('请输入任务目标'); return; }
    if (objective.trim().length < 5) { setError('任务目标至少5个字'); return; }
    try {
      const g = await api.createGoal(baseUrl, {
        objective: objective.trim(),
        criteria: ['任务完成'],
        max_steps: maxSteps,
        workspace: workspacePath,
      });
      setCurrentGoal(g);

      const run = await api.startRun(baseUrl, objective.trim(), workspacePath);
      setCurrentRunId(run.id);

      const loopResult = await api.runAgentLoop(baseUrl, run.id, maxSteps);
      setLoopStepCount(loopResult.steps);

      // Drive UI from the actual loop result, not blind assumption
      const derivedStatus = loopStatusToGoalStatus(loopResult.status, loopResult.steps, maxSteps);
      setCurrentGoal(prev => prev ? { ...prev, status: derivedStatus, step_count: loopResult.steps } : prev);

      if (loopResult.error) { setError(loopResult.error); }
    } catch (e) { setError(String(e)); }
  }

  async function handlePause() {
    if (!currentGoal) return;
    try {
      const g = await api.pauseGoal(baseUrl, currentGoal.id);
      setCurrentGoal(g);
    } catch (e) { setError(String(e)); }
  }

  async function handleResume() {
    if (!currentGoal) return;
    try {
      const g = await api.resumeGoal(baseUrl, currentGoal.id);
      setCurrentGoal(g);
      // Re-run agent loop after resume if we have a run
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
    try {
      const g = await api.clearGoal(baseUrl, currentGoal.id);
      setCurrentGoal(g);
      setCurrentRunId(null);
    } catch (e) { setError(String(e)); }
  }

  const displayGoal = currentGoal || goal;
  const status = displayGoal?.status ?? null;
  const stepCount = displayGoal?.step_count ?? loopStepCount;
  const isMaxed = stepCount >= maxSteps && maxSteps > 0;

  return <section className="goalConsole">
    <h2>长任务驾驶舱</h2>
    {!displayGoal ? <div className="goalCreate">
      <label>长任务目标 <input aria-label="长任务目标" value={objective} onChange={e => setObjective(e.target.value)} /></label>
      <button type="button" disabled={!canStart} onClick={handleStart}>开始长任务</button>
      {error ? <span className="error">{error}</span> : null}
    </div> : <div className="goalControl">
      <div className="statusBar">
        <strong>{status ? STATUS_LABEL[status as GoalStatus | 'rejected'] ?? status : ''}</strong>
        {status === 'paused' ? <span>等待人工批准</span> : null}
        {isMaxed && (status === 'stopped' || status === 'paused') ? <span>已达到最大步数</span> : null}
        <span>{stepCount} / {maxSteps}</span>
        <span>{displayGoal.objective}</span>
      </div>
      <div className="actions">
        {status === 'running' ? <button type="button" onClick={handlePause}>暂停任务</button> : null}
        {status === 'paused' ? <button type="button" onClick={handleResume}>恢复任务</button> : null}
        {status === 'running' || status === 'paused' ? <button type="button" onClick={handleStop}>停止任务</button> : null}
      </div>
      {error ? <span className="error">{error}</span> : null}
    </div>}
  </section>;
}
