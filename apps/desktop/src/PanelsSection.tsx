import { useState } from 'react';
import { CheckpointPanel } from './CheckpointPanel';
import ExecutionQueuePanel from './ExecutionQueuePanel';
import { GoalConsole } from './GoalConsole';
import { SideChatPanel } from './SideChatPanel';
import TaskClosurePanel from './TaskClosurePanel';
import type { AgentLoopResult } from '@bolt/shared';
import type { Goal, GoalEvidence, SteeringResult, TaskClosureEvidence, TaskTemplate, TimelineEvent, VerificationAssessment, VerificationPlan, ExecutionQueueItem } from '@bolt/shared/autonomy';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

interface PanelsProps {
  runId: string | null;
  goalInfo: Goal | null;
  unfinishedGoals: Goal[];
  workspace: string;
  baseUrl: string;
  fetcher?: Fetcher;
  onGoalChange: (g: Goal | null, rId: string | null) => void;
  api: {
    checkpoint: { createCheckpoint: (url: string, p: Record<string, unknown>) => Promise<unknown>; loadCheckpoint: (url: string, cpId: string) => Promise<unknown> };
    goal: { createGoal: (url: string, p: Record<string, unknown>) => Promise<Goal>; startRun: (url: string, g: string, ws: string) => Promise<{ id: string }>; runAgentLoop: (url: string, runId: string, steps: number) => Promise<AgentLoopResult>; pauseGoal: (url: string, id: string) => Promise<Goal>; resumeGoal: (url: string, id: string) => Promise<Goal>; clearGoal: (url: string, id: string) => Promise<Goal>; getGoal: (_url: string, _id: string) => Promise<Goal | null>; fetchGoalEvidence: (url: string, id: string) => Promise<GoalEvidence[]>; fetchRunTimeline: (url: string, runId: string) => Promise<TimelineEvent[]> };
    sideChat: { steerRun: (url: string, rId: string, content: string) => Promise<SteeringResult> };
    taskClosure: { fetchTaskTemplates: (b: string, f?: Fetcher) => Promise<TaskTemplate[]>; createTaskClosure: (b: string, p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; getTaskClosure: (b: string, id: string, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureEvent: (b: string, id: string, p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureReview: (b: string, id: string, p: { summary: string; passed: boolean }, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureRun: (b: string, id: string, runId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureGoal: (b: string, id: string, goalId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; fetchTaskClosureVerificationPlan: (b: string, id: string, f?: Fetcher) => Promise<VerificationPlan>; fetchTaskClosureAssessment: (b: string, id: string, f?: Fetcher) => Promise<VerificationAssessment>; updateTaskClosureAssessment: (b: string, id: string, f?: Fetcher) => Promise<TaskClosureEvidence> };
    executionQueue: { fetchExecutionQueue: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; proposeExecutionQueue: (b: string, closureId: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; approveExecutionQueueItem: (b: string, itemId: string, f?: Fetcher) => Promise<ExecutionQueueItem>; rejectExecutionQueueItem: (b: string, itemId: string, reason: string, f?: Fetcher) => Promise<ExecutionQueueItem>; completeExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem>; failExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem> };
  };
}

export function PanelsSection({ runId, goalInfo, unfinishedGoals, workspace, baseUrl, fetcher, onGoalChange, api }: PanelsProps) {
  const [closureId, setClosureId] = useState<string | null>(null);
  return (
    <>
      <CheckpointPanel runId={runId} goalId={goalInfo?.id ?? null} api={api.checkpoint} baseUrl={baseUrl} />
      <GoalConsole workspacePath={workspace} goal={goalInfo} api={api.goal} baseUrl={baseUrl} unfinishedGoals={unfinishedGoals} onGoalChange={onGoalChange} />
      <SideChatPanel runId={runId} api={api.sideChat} baseUrl={baseUrl} />
      <TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} runId={runId} goalId={goalInfo?.id ?? null} api={api.taskClosure} onClosureChange={setClosureId} />
      <ExecutionQueuePanel baseUrl={baseUrl} closureId={closureId} fetcher={fetcher} api={api.executionQueue} />
    </>
  );
}
