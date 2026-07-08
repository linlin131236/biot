import { useState } from 'react';
import { CheckpointPanel } from './CheckpointPanel';
import ExecutionHandoffPanel from './ExecutionHandoffPanel';
import ExecutionQueuePanel from './ExecutionQueuePanel';
import { GoalConsole } from './GoalConsole';
import { SideChatPanel } from './SideChatPanel';
import TaskClosurePanel from './TaskClosurePanel';
import { MemorySearchPanel } from './MemorySearchPanel';
import { MultiAgentStatusPanel } from './MultiAgentStatusPanel';
import { TaskHomePanel } from './TaskHomePanel';
import { PermissionCenterPanel } from './PermissionCenterPanel';
import { AuditTimelinePanel } from './AuditTimelinePanel';
import { DiagnosticsCenterPanel } from './DiagnosticsCenterPanel';
import { ReleaseReadinessPanel } from './ReleaseReadinessPanel';
import { MultiTaskQueuePanel } from './MultiTaskQueuePanel';
import { FailureExplanationPanel } from './FailureExplanationPanel';
import { SessionRecoveryPanel } from './SessionRecoveryPanel';
import { SettingsToolsPanel } from './SettingsToolsPanel';
import { PatchPreviewPanel } from './PatchPreviewPanel';
import { TestRunnerPanel } from './TestRunnerPanel';
import { ProductWorkbenchPanel } from './ProductWorkbenchPanel';
import { ResearcherPanel } from './ResearcherPanel';
import { BuilderPanel } from './BuilderPanel';
import { fetchMemoryDecisions, fetchMemoryFailures, fetchMemoryPreferences, fetchProjectProfile, fetchCodeMapEntries, fetchMultiAgentRoles, fetchSubtasksBoard, fetchSubtasks, fetchTaskHome, fetchPermissionCenter, approvePermissionFromCenter, rejectPermissionFromCenter, fetchAuditTimeline, fetchDiagnosticsCenter, fetchMultiTaskQueue, fetchFailureExplanation, fetchSessionRecovery, fetchSettingsTools, fetchPatchList, fetchPatchPreview, fetchProductWorkbench, fetchTestRunnerAvailable, runTest, fetchTestRunnerHistory, createResearchBrief, executeResearch, fetchResearchScopes, executeBuilderTask, fetchBuilderProposals } from './harnessClientAutonomy';
import type { AgentLoopResult } from '@bolt/shared';
import type { Goal, GoalEvidence, SteeringResult, TaskClosureEvidence, TaskTemplate, TimelineEvent, VerificationAssessment, VerificationPlan, ExecutionQueueItem, ExecutionHandoffRecord, ExecutionAuditTimelineEvent, ExecutionAuditDiagnostic, ExecutionAuditIntegrity } from '@bolt/shared/autonomy';
import type { LocalReleaseChecklist, RecoveryPolicy, ReleaseReadiness, TaskGraphSummary } from '@bolt/shared/release';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface PanelsProps {
  runId: string | null;
  goalInfo: Goal | null;
  unfinishedGoals: Goal[];
  workspace: string;
  baseUrl: string;
  fetcher?: Fetcher;
  onGoalChange: (g: Goal | null, rId: string | null) => void;
  api: {
    checkpoint: { createCheckpoint: (url: string, p: Record<string, unknown>) => Promise<unknown>; loadCheckpoint: (url: string, cpId: string) => Promise<unknown> };
    goal: { createGoal: (url: string, p: Record<string, unknown>) => Promise<Goal>; startRun: (url: string, g: string, ws: string) => Promise<{ id: string }>; runAgentLoop: (url: string, runId: string, steps: number) => Promise<AgentLoopResult>; pauseGoal: (url: string, id: string) => Promise<Goal>; resumeGoal: (url: string, id: string) => Promise<Goal>; clearGoal: (url: string, id: string) => Promise<Goal>; getGoal: (_url: string, _id: string) => Promise<Goal | null>; fetchGoalEvidence: (url: string, id: string) => Promise<GoalEvidence[]>; fetchRunTimeline: (url: string, runId: string) => Promise<TimelineEvent[]>; fetchTaskResultSummary: (url: string, closureId: string) => Promise<Record<string, unknown>>; getTaskClosureByRun: (url: string, runId: string) => Promise<TaskClosureEvidence> };
    sideChat: { steerRun: (url: string, rId: string, content: string) => Promise<SteeringResult> };
    taskClosure: { fetchTaskTemplates: (b: string, f?: Fetcher) => Promise<TaskTemplate[]>; createTaskClosure: (b: string, p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; getTaskClosure: (b: string, id: string, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureEvent: (b: string, id: string, p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureReview: (b: string, id: string, p: { summary: string; passed: boolean }, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureRun: (b: string, id: string, runId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureGoal: (b: string, id: string, goalId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; fetchTaskClosureVerificationPlan: (b: string, id: string, f?: Fetcher) => Promise<VerificationPlan>; fetchTaskClosureAssessment: (b: string, id: string, f?: Fetcher) => Promise<VerificationAssessment>; updateTaskClosureAssessment: (b: string, id: string, f?: Fetcher) => Promise<TaskClosureEvidence> };
    executionQueue: { fetchExecutionQueue: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; proposeExecutionQueue: (b: string, closureId: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; approveExecutionQueueItem: (b: string, itemId: string, f?: Fetcher) => Promise<ExecutionQueueItem>; rejectExecutionQueueItem: (b: string, itemId: string, reason: string, f?: Fetcher) => Promise<ExecutionQueueItem>; completeExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem>; failExecutionQueueItem: (b: string, itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem> };
    executionHandoff: { fetchExecutionHandoffs: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionHandoffRecord[]>; fetchExecutionAuditTimeline: (b: string, closureId: string, f?: Fetcher) => Promise<ExecutionAuditTimelineEvent[]>; fetchExecutionAuditDiagnostics: (b: string, closureId?: string, f?: Fetcher) => Promise<ExecutionAuditDiagnostic[]>; fetchExecutionAuditIntegrity: (b: string, f?: Fetcher) => Promise<ExecutionAuditIntegrity[]>; fetchReleaseReadiness: (b: string, f?: Fetcher) => Promise<ReleaseReadiness>; fetchLocalReleaseChecklist: (b: string, f?: Fetcher) => Promise<LocalReleaseChecklist>; fetchRecoveryPolicy: (b: string, f?: Fetcher) => Promise<RecoveryPolicy>; fetchPlannerGraphs: (b: string, f?: Fetcher) => Promise<TaskGraphSummary[]>; createExecutionHandoff: (b: string, itemId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; completeExecutionHandoff: (b: string, handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; failExecutionHandoff: (b: string, handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; requestExecutionHandoffPermission: (b: string, handoffId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord> };
    researcher: { createBrief: (b: string, p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; executeResearch: (b: string, briefId: string, f: Fetcher) => Promise<Record<string, unknown>>; fetchScopes: (b: string, f: Fetcher) => Promise<Record<string, unknown>> };
    builder: { executeTask: (b: string, p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchProposals: (b: string, f: Fetcher) => Promise<Record<string, unknown>> };
  };
}

export type PanelsApi = PanelsProps['api'];

export function PanelsSection({ runId, goalInfo, unfinishedGoals, workspace, baseUrl, fetcher, onGoalChange, api }: PanelsProps) {
  const [closureId, setClosureId] = useState<string | null>(null);
  const [approvedQueueItemId, setApprovedQueueItemId] = useState<string | null>(null);
  function handleClosureChange(nextClosureId: string | null) {
    if (nextClosureId !== closureId) setApprovedQueueItemId(null);
    setClosureId(nextClosureId);
  }
  return (
    <>
      <ProductWorkbenchPanel baseUrl={baseUrl} api={{ fetchProductWorkbench }} />
      <TaskHomePanel baseUrl={baseUrl} api={{ fetchTaskHome }} />
      <PermissionCenterPanel baseUrl={baseUrl} api={{
        fetchPermissionCenter,
        grantPermission: (url, requestId) => approvePermissionFromCenter(url, requestId, fetcher),
        denyPermission: (url, requestId) => rejectPermissionFromCenter(url, requestId, fetcher),
      }} />
      <AuditTimelinePanel baseUrl={baseUrl} closureId={closureId} api={{ fetchAuditTimeline }} />
      <DiagnosticsCenterPanel baseUrl={baseUrl} api={{ fetchDiagnosticsCenter }} />
      <ReleaseReadinessPanel baseUrl={baseUrl} api={{
        fetchReleaseReadiness: api.executionHandoff.fetchReleaseReadiness,
        fetchLocalChecklist: api.executionHandoff.fetchLocalReleaseChecklist,
        fetchRecoveryPolicy: api.executionHandoff.fetchRecoveryPolicy,
      }} />
      <MultiTaskQueuePanel baseUrl={baseUrl} api={{ fetchMultiTaskQueue }} />
      <FailureExplanationPanel baseUrl={baseUrl} api={{ fetchFailureExplanation }} />
      <SessionRecoveryPanel baseUrl={baseUrl} api={{ fetchSessionRecovery }} />
      <SettingsToolsPanel baseUrl={baseUrl} api={{ fetchSettingsTools }} />
      <PatchPreviewPanel
        fetchPatchList={() => fetchPatchList(baseUrl, fetcher) as Promise<{ patches: { patch_id: string; description: string; risk_level: string; risk_label: string; status: string; status_label: string; total_files: number; total_lines: number; audit_hash: string }[] }>}
        fetchPatchPreview={(patchId: string) => fetchPatchPreview(baseUrl, patchId, fetcher) as Promise<{ patch_id: string; description: string; risk_level: string; risk_label: string; total_files: number; total_lines: number; files: { path: string; operation: string; hunk_count: number }[]; unified_diff: string; disclaimer: string }>}
      />
      <TestRunnerPanel baseUrl={baseUrl} api={{ fetchAvailableTests: fetchTestRunnerAvailable, runTest, fetchTestHistory: fetchTestRunnerHistory }} />
      <CheckpointPanel runId={runId} goalId={goalInfo?.id ?? null} api={api.checkpoint} baseUrl={baseUrl} />
      <GoalConsole workspacePath={workspace} goal={goalInfo} api={{ ...api.goal, fetchTaskResultSummary: (url, closureId) => fetchTaskResultSummary(url, closureId, fetcher), getTaskClosureByRun: (url, runId) => getTaskClosureByRun(url, runId, fetcher) }} baseUrl={baseUrl} unfinishedGoals={unfinishedGoals} onGoalChange={onGoalChange} />
      <SideChatPanel runId={runId} api={api.sideChat} baseUrl={baseUrl} />
      <TaskClosurePanel baseUrl={baseUrl} workspace={workspace} fetcher={fetcher} runId={runId} goalId={goalInfo?.id ?? null} api={api.taskClosure} onClosureChange={handleClosureChange} />
      <ExecutionQueuePanel baseUrl={baseUrl} closureId={closureId} fetcher={fetcher} api={api.executionQueue} onApprovedItemChange={setApprovedQueueItemId} />
      <ExecutionHandoffPanel baseUrl={baseUrl} closureId={closureId} selectedQueueItemId={approvedQueueItemId} fetcher={fetcher} api={api.executionHandoff} />
      <MemorySearchPanel baseUrl={baseUrl} api={{
        fetchDecisions: fetchMemoryDecisions,
        fetchFailures: fetchMemoryFailures,
        fetchPreferences: fetchMemoryPreferences,
        fetchProfile: fetchProjectProfile,
        fetchCodeMap: fetchCodeMapEntries,
      }} />
      <MultiAgentStatusPanel baseUrl={baseUrl} api={{
        fetchRoles: fetchMultiAgentRoles,
        fetchBoard: fetchSubtasksBoard,
        fetchSubtasks: fetchSubtasks,
      }} />
      <ResearcherPanel baseUrl={baseUrl} api={{ createBrief: createResearchBrief, executeResearch, fetchScopes: fetchResearchScopes }} />
      <BuilderPanel baseUrl={baseUrl} api={{ executeTask: executeBuilderTask, fetchProposals: fetchBuilderProposals }} />
    </>
  );
}
