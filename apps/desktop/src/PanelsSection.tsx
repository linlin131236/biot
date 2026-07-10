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
import { ReviewerPanel } from './ReviewerPanel';
import { SkillLearnerPanel } from './SkillLearnerPanel';
import { OrchestratorPanel } from './OrchestratorPanel';
import { SleepWakePanel } from './SleepWakePanel';
import { GateFreezePanel } from './GateFreezePanel';
import { ToolVerificationPanel } from './ToolVerificationPanel';
import { AutoFixPanel } from './AutoFixPanel';
import { AutoContinuePanel } from './AutoContinuePanel';
import { AutonomousLoopPanel } from './AutonomousLoopPanel';
import { DesktopBetaShipPanel } from './DesktopBetaShipPanel';
import { fetchMemoryDecisions, fetchMemoryFailures, fetchMemoryPreferences, fetchProjectProfile, fetchCodeMapEntries, fetchMultiAgentRoles, fetchSubtasksBoard, fetchSubtasks, fetchTaskHome, fetchPermissionCenter, approvePermissionFromCenter, rejectPermissionFromCenter, fetchAuditTimeline, fetchDiagnosticsCenter, fetchMultiTaskQueue, fetchFailureExplanation, fetchSessionRecovery, fetchSettingsTools, fetchPatchList, fetchPatchPreview, fetchProductWorkbench, fetchTestRunnerAvailable, runTest, fetchTestRunnerHistory, createResearchBrief, executeResearch, fetchResearchScopes, executeBuilderTask, fetchBuilderProposals, reviewBuilderOutput, fetchReviewVerdictLabel, runOrchestrator, fetchOrchestratorRoles, sleepAgent, wakeAgent, fetchSleepWakeStatus, freezeGate, unfreezeGate, fetchGateStatus, verifyTools, autoFixReviewFindings, autoContinueOrchestration, fetchAutoContinueStatus, runAutonomousLoop } from './harnessClientAutonomy';
import type { AgentLoopResult } from '@bolt/shared';
import type { Goal, GoalEvidence, SteeringResult, TaskClosureEvidence, TaskTemplate, TimelineEvent, VerificationAssessment, VerificationPlan, ExecutionQueueItem, ExecutionHandoffRecord, ExecutionAuditTimelineEvent, ExecutionAuditDiagnostic, ExecutionAuditIntegrity } from '@bolt/shared/autonomy';
import type { LocalReleaseChecklist, RecoveryPolicy, ReleaseReadiness, TaskGraphSummary } from '@bolt/shared/release';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export interface PanelsProps {
  runId: string | null;
  goalInfo: Goal | null;
  unfinishedGoals: Goal[];
  workspace: string;
  fetcher: Fetcher;
  onGoalChange: (g: Goal | null, rId: string | null) => void;
  api: {
    checkpoint: { createCheckpoint: (p: Record<string, unknown>) => Promise<unknown>; loadCheckpoint: (cpId: string) => Promise<unknown> };
    goal: { createGoal: (p: Record<string, unknown>) => Promise<Goal>; startRun: (g: string, ws: string) => Promise<{ id: string }>; runAgentLoop: (runId: string, steps: number) => Promise<AgentLoopResult>; pauseGoal: (id: string) => Promise<Goal>; resumeGoal: (id: string) => Promise<Goal>; clearGoal: (id: string) => Promise<Goal>; getGoal: (_id: string) => Promise<Goal | null>; fetchGoalEvidence: (id: string) => Promise<GoalEvidence[]>; fetchRunTimeline: (runId: string) => Promise<TimelineEvent[]>; fetchTaskResultSummary: (closureId: string) => Promise<Record<string, unknown>>; getTaskClosureByRun: (runId: string) => Promise<TaskClosureEvidence> };
    sideChat: { steerRun: (rId: string, content: string) => Promise<SteeringResult> };
    taskClosure: { fetchTaskTemplates: (f?: Fetcher) => Promise<TaskTemplate[]>; createTaskClosure: (p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; getTaskClosure: (id: string, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureEvent: (id: string, p: Record<string, unknown>, f?: Fetcher) => Promise<TaskClosureEvidence>; addClosureReview: (id: string, p: { summary: string; passed: boolean }, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureRun: (id: string, runId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; bindTaskClosureGoal: (id: string, goalId: string, f?: Fetcher) => Promise<TaskClosureEvidence>; fetchTaskClosureVerificationPlan: (id: string, f?: Fetcher) => Promise<VerificationPlan>; fetchTaskClosureAssessment: (id: string, f?: Fetcher) => Promise<VerificationAssessment>; updateTaskClosureAssessment: (id: string, f?: Fetcher) => Promise<TaskClosureEvidence> };
    executionQueue: { fetchExecutionQueue: (closureId?: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; proposeExecutionQueue: (closureId: string, f?: Fetcher) => Promise<ExecutionQueueItem[]>; approveExecutionQueueItem: (itemId: string, f?: Fetcher) => Promise<ExecutionQueueItem>; rejectExecutionQueueItem: (itemId: string, reason: string, f?: Fetcher) => Promise<ExecutionQueueItem>; completeExecutionQueueItem: (itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem>; failExecutionQueueItem: (itemId: string, result: string, f?: Fetcher) => Promise<ExecutionQueueItem> };
    executionHandoff: { fetchExecutionHandoffs: (closureId?: string, f?: Fetcher) => Promise<ExecutionHandoffRecord[]>; fetchExecutionAuditTimeline: (closureId: string, f?: Fetcher) => Promise<ExecutionAuditTimelineEvent[]>; fetchExecutionAuditDiagnostics: (closureId?: string, f?: Fetcher) => Promise<ExecutionAuditDiagnostic[]>; fetchExecutionAuditIntegrity: (f?: Fetcher) => Promise<ExecutionAuditIntegrity[]>; fetchReleaseReadiness: (f?: Fetcher) => Promise<ReleaseReadiness>; fetchLocalReleaseChecklist: (f?: Fetcher) => Promise<LocalReleaseChecklist>; fetchRecoveryPolicy: (f?: Fetcher) => Promise<RecoveryPolicy>; fetchPlannerGraphs: (f?: Fetcher) => Promise<TaskGraphSummary[]>; createExecutionHandoff: (itemId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; completeExecutionHandoff: (handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; failExecutionHandoff: (handoffId: string, result: string, f?: Fetcher) => Promise<ExecutionHandoffRecord>; requestExecutionHandoffPermission: (handoffId: string, f?: Fetcher) => Promise<ExecutionHandoffRecord> };
    researcher: { createBrief: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; executeResearch: (briefId: string, f: Fetcher) => Promise<Record<string, unknown>>; fetchScopes: (f: Fetcher) => Promise<Record<string, unknown>> };
    builder: { executeTask: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchProposals: (f: Fetcher) => Promise<Record<string, unknown>> };
    reviewer: { reviewOutput: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchVerdictLabel: (verdict: string, f: Fetcher) => Promise<Record<string, unknown>> };
    skilllearner: { autoScan: (k: string, f: Fetcher) => Promise<Record<string, unknown>>; recordFailure: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>> };
    orchestrator: { runOrchestration: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchRoles: (f: Fetcher) => Promise<Record<string, unknown>> };
    sleepWake: { sleep: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; wake: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchStatus: (f: Fetcher) => Promise<Record<string, unknown>> };
    gateFreeze: { freezeGate: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; unfreezeGate: (f: Fetcher) => Promise<Record<string, unknown>>; fetchStatus: (f: Fetcher) => Promise<Record<string, unknown>> };
    toolVerification: { verifyTools: (f: Fetcher) => Promise<Record<string, unknown>> };
    autoFix: { autoFixReviewFindings: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>> };
    autoContinue: { autoContinue: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>>; fetchStatus: (f: Fetcher) => Promise<Record<string, unknown>> };
    autonomousLoop: { runLoop: (p: Record<string, unknown>, f: Fetcher) => Promise<Record<string, unknown>> };
    desktopBetaShip?: { fetchBetaShip: (f: Fetcher) => Promise<Record<string, unknown>> };
  };
}

export type PanelsApi = PanelsProps['api'];

export function PanelsSection({ runId, goalInfo, unfinishedGoals, workspace, fetcher, onGoalChange, api }: PanelsProps) {
  const [closureId, setClosureId] = useState<string | null>(null);
  const [approvedQueueItemId, setApprovedQueueItemId] = useState<string | null>(null);
  function handleClosureChange(nextClosureId: string | null) {
    if (nextClosureId !== closureId) setApprovedQueueItemId(null);
    setClosureId(nextClosureId);
  }
  return (
    <>
      <ProductWorkbenchPanel api={{ fetchProductWorkbench: () => fetchProductWorkbench(fetcher) }} />
      <TaskHomePanel api={{ fetchTaskHome: () => fetchTaskHome(fetcher) }} />
      <PermissionCenterPanel api={{
        fetchPermissionCenter: () => fetchPermissionCenter(fetcher),
        grantPermission: (requestId) => approvePermissionFromCenter(requestId, fetcher),
        denyPermission: (requestId) => rejectPermissionFromCenter(requestId, fetcher),
      }} />
      <AuditTimelinePanel closureId={closureId} api={{ fetchAuditTimeline: (id) => fetchAuditTimeline(id, undefined, fetcher) }} />
      <DiagnosticsCenterPanel api={{ fetchDiagnosticsCenter: () => fetchDiagnosticsCenter(fetcher) }} />
      <ReleaseReadinessPanel api={{
        fetchReleaseReadiness: api.executionHandoff.fetchReleaseReadiness,
        fetchLocalChecklist: api.executionHandoff.fetchLocalReleaseChecklist,
        fetchRecoveryPolicy: api.executionHandoff.fetchRecoveryPolicy,
      }} />
      <MultiTaskQueuePanel api={{ fetchMultiTaskQueue: () => fetchMultiTaskQueue(fetcher) }} />
      <FailureExplanationPanel api={{ fetchFailureExplanation: () => fetchFailureExplanation(fetcher) }} />
      <SessionRecoveryPanel api={{ fetchSessionRecovery: () => fetchSessionRecovery(fetcher) }} />
      <SettingsToolsPanel api={{ fetchSettingsTools: () => fetchSettingsTools(fetcher) }} />
      <PatchPreviewPanel
        fetchPatchList={() => fetchPatchList(fetcher) as Promise<{ patches: { patch_id: string; description: string; risk_level: string; risk_label: string; status: string; status_label: string; total_files: number; total_lines: number; audit_hash: string }[] }>}
        fetchPatchPreview={(patchId: string) => fetchPatchPreview(patchId, fetcher) as Promise<{ patch_id: string; description: string; risk_level: string; risk_label: string; total_files: number; total_lines: number; files: { path: string; operation: string; hunk_count: number }[]; unified_diff: string; disclaimer: string }>}
      />
      <TestRunnerPanel api={{
        fetchAvailableTests: () => fetchTestRunnerAvailable(fetcher),
        runTest: (id, args) => runTest(id, args, fetcher),
        fetchTestHistory: () => fetchTestRunnerHistory(fetcher),
      }} />
      <CheckpointPanel runId={runId} goalId={goalInfo?.id ?? null} api={api.checkpoint} />
      <GoalConsole workspacePath={workspace} goal={goalInfo} api={{ ...api.goal, fetchTaskResultSummary: (closureId) => fetchTaskResultSummary(closureId, fetcher), getTaskClosureByRun: (runId) => getTaskClosureByRun(runId, fetcher) }} unfinishedGoals={unfinishedGoals} onGoalChange={onGoalChange} />
      <SideChatPanel runId={runId} api={api.sideChat} />
      <TaskClosurePanel workspace={workspace} fetcher={fetcher} runId={runId} goalId={goalInfo?.id ?? null} api={api.taskClosure} onClosureChange={handleClosureChange} />
      <ExecutionQueuePanel closureId={closureId} fetcher={fetcher} api={api.executionQueue} onApprovedItemChange={setApprovedQueueItemId} />
      <ExecutionHandoffPanel closureId={closureId} selectedQueueItemId={approvedQueueItemId} fetcher={fetcher} api={api.executionHandoff} />
      <MemorySearchPanel api={{
        fetchDecisions: (keyword) => fetchMemoryDecisions(keyword, fetcher),
        fetchFailures: (keyword) => fetchMemoryFailures(keyword, fetcher),
        fetchPreferences: (keyword) => fetchMemoryPreferences(keyword, fetcher),
        fetchProfile: () => fetchProjectProfile(fetcher),
        fetchCodeMap: (keyword) => fetchCodeMapEntries(keyword, fetcher),
      }} />
      <MultiAgentStatusPanel api={{
        fetchRoles: () => fetchMultiAgentRoles(fetcher),
        fetchBoard: () => fetchSubtasksBoard(fetcher),
        fetchSubtasks: (role, status) => fetchSubtasks(role, status, fetcher),
      }} />
      <ResearcherPanel fetcher={fetcher} api={{ createBrief: createResearchBrief, executeResearch, fetchScopes: fetchResearchScopes }} />
      <BuilderPanel fetcher={fetcher} api={{ executeTask: executeBuilderTask, fetchProposals: fetchBuilderProposals }} />
      <ReviewerPanel fetcher={fetcher} api={{ reviewOutput: reviewBuilderOutput, fetchVerdictLabel: fetchReviewVerdictLabel }} />
      <SkillLearnerPanel fetcher={fetcher} api={{ autoScan: api.skilllearner.autoScan, recordFailure: api.skilllearner.recordFailure }} />
      <OrchestratorPanel fetcher={fetcher} api={{ runOrchestration: runOrchestrator, fetchRoles: fetchOrchestratorRoles }} />
      <SleepWakePanel api={{ sleep: api.sleepWake.sleep, wake: api.sleepWake.wake, fetchStatus: api.sleepWake.fetchStatus }} />
      <GateFreezePanel fetcher={fetcher} api={{ freezeGate: api.gateFreeze.freezeGate, unfreezeGate: api.gateFreeze.unfreezeGate, fetchGateStatus: api.gateFreeze.fetchStatus }} />
      <ToolVerificationPanel fetcher={fetcher} api={{ verifyTools: api.toolVerification.verifyTools }} />
      <AutoFixPanel fetcher={fetcher} api={{ autoFixReviewFindings: api.autoFix.autoFixReviewFindings }} />
      <AutoContinuePanel fetcher={fetcher} api={{ autoContinue: api.autoContinue.autoContinue, fetchAutoContinueStatus: api.autoContinue.fetchStatus }} />
      <AutonomousLoopPanel fetcher={fetcher} api={{ runAutonomousLoop: api.autonomousLoop.runLoop }} />
      {api.desktopBetaShip && <DesktopBetaShipPanel fetcher={fetcher} api={{ fetchBetaShip: api.desktopBetaShip.fetchBetaShip }} />}
    </>
  );
}
