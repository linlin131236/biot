/** Autonomy API client methods: Goal, Conversation, Vector Memory, Skill, Delegation, Checkpoint.
 *  Split from harnessClient.ts to respect the 300-line size gate.
 */
import type {
  Goal, ConversationMessage, SkillManifest, DelegationTask,
  Checkpoint, ReviewChecklist, ReviewResult,
  TimelineEvent, GoalEvidence, SteeringResult,
  TaskTemplate, TaskClosureEvidence, VerificationPlan, VerificationAssessment,
  ExecutionQueueItem, ExecutionHandoffRecord, ExecutionAuditTimelineEvent, ExecutionAuditDiagnostic,
  ExecutionAuditIntegrity,
} from '@bolt/shared/autonomy';
import type { AllowedTransitions, LocalReleaseChecklist, RecoveryPolicy, ReleaseReadiness, StateMachineSummary, TaskGraph, TaskGraphSummary, TaskNode, TransitionResult } from '@bolt/shared/release';

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

// === Goal API ===
export async function createGoal(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Goal> {
  return readJson(await fetcher('/goals', jsonPost(payload)));
}

export async function getGoal(goalId: string, fetcher: Fetcher): Promise<Goal> {
  return readJson(await fetcher(`/goals/${goalId}`));
}

export async function pauseGoal(goalId: string, fetcher: Fetcher): Promise<Goal> {
  return readJson(await fetcher(`/goals/${goalId}/pause`, { method: 'POST' }));
}

export async function resumeGoal(goalId: string, fetcher: Fetcher): Promise<Goal> {
  return readJson(await fetcher(`/goals/${goalId}/resume`, { method: 'POST' }));
}

export async function fetchUnfinishedGoals(fetcher: Fetcher): Promise<Goal[]> {
  return readJson(await fetcher('/goals/unfinished'));
}

export async function clearGoal(goalId: string, fetcher: Fetcher): Promise<Goal> {
  return readJson(await fetcher(`/goals/${goalId}/clear`, { method: 'POST' }));
}

export async function fetchGoalEvidence(goalId: string, fetcher: Fetcher): Promise<GoalEvidence[]> {
  return readJson(await fetcher(`/goals/${goalId}/evidence`));
}

export async function fetchGoalBudget(goalId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/goals/${goalId}/budget`));
}

// Re-export the typed runAgentLoop from harnessClient (uses jsonPost with content-type header).
export { runAgentLoop } from './harnessClient';

// === Conversation API ===
export async function createConversation(payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ id: string }> {
  return readJson(await fetcher('/conversations', jsonPost(payload)));
}

export async function listConversations(fetcher: Fetcher): Promise<string[]> {
  return readJson(await fetcher('/conversations'));
}

export async function getConversation(conversationId: string, fetcher: Fetcher): Promise<ConversationMessage[]> {
  return readJson(await fetcher(`/conversations/${conversationId}`));
}

export async function addMessage(conversationId: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<{ status: string }> {
  return readJson(await fetcher(`/conversations/${conversationId}/messages`, jsonPost(payload)));
}

// === Timeline / Steering ===
export async function steerRun(runId: string, content: string, fetcher: Fetcher): Promise<SteeringResult> {
  return readJson(await fetcher(`/runs/${runId}/steering`, jsonPost({ content })));
}

export async function fetchRunTimeline(runId: string, fetcher: Fetcher): Promise<TimelineEvent[]> {
  return readJson(await fetcher(`/runs/${runId}/timeline`));
}

// === Skill API (read-only via harness) ===
export async function fetchSkills(fetcher: Fetcher): Promise<SkillManifest[]> {
  void fetcher;
  return [];
}

// === Checkpoint API ===
export async function createCheckpoint(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Checkpoint> {
  return readJson(await fetcher('/checkpoints', jsonPost(payload)));
}

export async function loadCheckpoint(cpId: string, fetcher: Fetcher): Promise<Checkpoint | null> {
  return readJson(await fetcher(`/checkpoints/${cpId}`));
}

// === Task Closure API ===
export async function fetchTaskTemplates(fetcher: Fetcher): Promise<TaskTemplate[]> {
  return readJson(await fetcher('/task-closures/templates'));
}

export async function createTaskClosure(payload: { objective: string; template_id: string; run_id?: string; goal_id?: string }, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher('/task-closures', jsonPost(payload)));
}

export async function getTaskClosure(closureId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}`));
}

export async function bindTaskClosureRun(closureId: string, runId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}/bind-run`, jsonPost({ run_id: runId })));
}

export async function bindTaskClosureGoal(closureId: string, goalId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}/bind-goal`, jsonPost({ goal_id: goalId })));
}

export async function getTaskClosureByRun(runId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/by-run/${runId}`));
}

export async function getTaskClosureByGoal(goalId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/by-goal/${goalId}`));
}

export async function addClosureEvent(closureId: string, payload: Record<string, unknown>, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}/events`, jsonPost(payload)));
}

export async function addClosureReview(closureId: string, payload: { summary: string; passed: boolean }, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}/review`, jsonPost(payload)));
}

export async function fetchTaskClosureVerificationPlan(closureId: string, fetcher: Fetcher): Promise<VerificationPlan> {
  return readJson(await fetcher(`/task-closures/${closureId}/verification-plan`));
}

export async function fetchTaskClosureAssessment(closureId: string, fetcher: Fetcher): Promise<VerificationAssessment> {
  return readJson(await fetcher(`/task-closures/${closureId}/assessment`));
}

export async function updateTaskClosureAssessment(closureId: string, fetcher: Fetcher): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`/task-closures/${closureId}/assessment`, jsonPost({})));
}

export async function fetchTaskResultSummary(closureId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/task-closures/${encodeURIComponent(closureId)}/result-summary`));
}

export async function fetchExecutionQueue(closureId: string | undefined, fetcher: Fetcher): Promise<ExecutionQueueItem[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`/execution-queue${query}`));
}

export async function proposeExecutionQueue(closureId: string, fetcher: Fetcher): Promise<ExecutionQueueItem[]> {
  return readJson(await fetcher(`/task-closures/${closureId}/execution-queue/propose`, jsonPost({})));
}

export async function approveExecutionQueueItem(itemId: string, fetcher: Fetcher): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`/execution-queue/${itemId}/approve`, jsonPost({})));
}

export async function rejectExecutionQueueItem(itemId: string, reason: string, fetcher: Fetcher): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`/execution-queue/${itemId}/reject`, jsonPost({ reason })));
}

export async function completeExecutionQueueItem(itemId: string, result: string, fetcher: Fetcher): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`/execution-queue/${itemId}/complete`, jsonPost({ result })));
}

export async function failExecutionQueueItem(itemId: string, result: string, fetcher: Fetcher): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`/execution-queue/${itemId}/fail`, jsonPost({ result })));
}

export async function fetchExecutionHandoffs(closureId: string | undefined, fetcher: Fetcher): Promise<ExecutionHandoffRecord[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`/execution-handoffs${query}`));
}

export async function createExecutionHandoff(itemId: string, fetcher: Fetcher): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`/execution-queue/${itemId}/handoff`, jsonPost({})));
}

export async function completeExecutionHandoff(handoffId: string, result: string, fetcher: Fetcher): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`/execution-handoffs/${handoffId}/complete`, jsonPost({ result })));
}

export async function failExecutionHandoff(handoffId: string, result: string, fetcher: Fetcher): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`/execution-handoffs/${handoffId}/fail`, jsonPost({ result })));
}

export async function requestExecutionHandoffPermission(handoffId: string, fetcher: Fetcher): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`/execution-handoffs/${handoffId}/request-permission`, jsonPost({})));
}

export async function fetchExecutionAuditTimeline(closureId: string, fetcher: Fetcher): Promise<ExecutionAuditTimelineEvent[]> {
  return readJson(await fetcher(`/task-closures/${encodeURIComponent(closureId)}/execution-audit-timeline`));
}

export async function fetchExecutionAuditDiagnostics(closureId: string | undefined, fetcher: Fetcher): Promise<ExecutionAuditDiagnostic[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`/execution-audit/diagnostics${query}`));
}

export async function fetchExecutionAuditIntegrity(fetcher: Fetcher): Promise<ExecutionAuditIntegrity[]> {
  return readJson(await fetcher('/execution-audit/integrity'));
}

export async function fetchReleaseReadiness(fetcher: Fetcher): Promise<ReleaseReadiness> {
  return readJson(await fetcher('/release-readiness'));
}

export async function fetchLocalReleaseChecklist(fetcher: Fetcher): Promise<LocalReleaseChecklist> {
  return readJson(await fetcher('/local-release-checklist'));
}

export async function fetchRecoveryPolicy(fetcher: Fetcher): Promise<RecoveryPolicy> {
  return readJson(await fetcher('/recovery-policy'));
}

// === Planner Task Graph API (M61) ===
export async function fetchPlannerGraphs(fetcher: Fetcher): Promise<TaskGraphSummary[]> {
  return readJson(await fetcher('/planner/graphs'));
}

export async function createPlannerGraph(payload: { title: string; objective: string }, fetcher: Fetcher): Promise<TaskGraph> {
  return readJson(await fetcher('/planner/graphs', jsonPost(payload)));
}

export async function fetchPlannerGraph(graphId: string, fetcher: Fetcher): Promise<TaskGraph> {
  return readJson(await fetcher(`/planner/graphs/${graphId}`));
}

export async function addPlannerNode(graphId: string, payload: { title: string; dependencies?: string[]; risk?: string; owner_role?: string; evidence_refs?: string[] }, fetcher: Fetcher): Promise<TaskNode> {
  return readJson(await fetcher(`/planner/graphs/${graphId}/nodes`, jsonPost(payload)));
}

export async function updatePlannerNodeStatus(graphId: string, nodeId: string, status: string, fetcher: Fetcher): Promise<TaskNode> {
  return readJson(await fetcher(`/planner/graphs/${graphId}/nodes/${nodeId}`, {
    ...jsonPost({ status }),
    method: 'PATCH',
  }));
}

// === Execution State Machine API (M62) ===
export async function fetchStateMachineSummary(fetcher: Fetcher): Promise<StateMachineSummary> {
  return readJson(await fetcher('/execution/state-machine/summary'));
}

export async function validateTransition(payload: { from_state: string; to_state: string; node_id?: string; reason?: string }, fetcher: Fetcher): Promise<TransitionResult> {
  return readJson(await fetcher('/execution/state-machine/validate', jsonPost(payload)));
}

// === Review Gate ===
export async function evaluateReview(payload: { items: string[]; results: Record<string, boolean> }, fetcher: Fetcher): Promise<ReviewResult> {
  return readJson(await fetcher('/review/evaluate', jsonPost(payload)));
}

// === Memory Search (M79) ===
export async function fetchMemoryDecisions(keyword: string, fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`/decisions/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchMemoryFailures(keyword: string, fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`/failures/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchMemoryPreferences(keyword: string, fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`/preferences/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchProjectProfile(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/project/profile'));
}
export async function fetchCodeMapEntries(keyword: string, fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`/code-map/query?keyword=${encodeURIComponent(keyword)}`));
}

// === Multi-Agent Status (M87) ===
export async function fetchMultiAgentRoles(fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher('/roles'));
}
export async function fetchSubtasksBoard(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/subtasks/board/summary'));
}
export async function fetchSubtasks(role: string | undefined, status: string | undefined, fetcher: Fetcher): Promise<Record<string, unknown>[]> {
  const params = new URLSearchParams();
  if (role) params.set('role', role);
  if (status) params.set('status', status);
  return readJson(await fetcher(`/subtasks?${params.toString()}`));
}

// === Task Home (M91) ===
export async function fetchTaskHome(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/task-home'));
}

// === Permission Center (M92) ===
export async function fetchPermissionCenter(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/permission-center'));
}

export async function approvePermissionFromCenter(requestId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/permissions/${requestId}/approve`, { method: 'POST' }));
}

export async function rejectPermissionFromCenter(requestId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/permissions/${requestId}/reject`, { method: 'POST' }));
}

export async function applyApproval(proposalId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/approval/apply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ proposal_id: proposalId, approval: {} }),
  }));
}

// === Audit Timeline (M93) ===
export async function fetchAuditTimeline(closureId: string | undefined, source: string | undefined, fetcher: Fetcher): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (closureId) params.set("closure_id", closureId);
  if (source) params.set("source", source);
  const qs = params.toString();
  return readJson(await fetcher(`/audit-timeline${qs ? `?${qs}` : ""}`));
}

// === Diagnostics Center (M94) ===
export async function fetchDiagnosticsCenter(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/diagnostics-center'));
}

// === Multi Task Queue (M96) ===
export async function fetchMultiTaskQueue(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/multi-task-queue'));
}

// === Failure Explanation (M97) ===
export async function fetchFailureExplanation(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/failure-explanation'));
}

// === Session Recovery (M98) ===
export async function fetchSessionRecovery(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/session-recovery'));
}

// === Settings Tools (M99) ===
export async function fetchSettingsTools(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/settings-tools'));
}

// === Test Runner (M157) ===
export async function fetchTestRunnerAvailable(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/test-runner/available'));
}

export async function runTest(testId: string, extraArgs: string[] = [], fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/test-runner/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ test_id: testId, extra_args: extraArgs }),
  }));
}

export async function fetchTestRunnerHistory(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/test-runner/history'));
}

// === Patch Proposal (M107) ===
export async function fetchPatchList(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/patch/list'));
}

export async function fetchPatchPreview(patchId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/tools/patch/${patchId}/preview`));
}

// === Product Workbench (M126) ===
export async function fetchProductWorkbench(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/product-workbench'));
}

// === Researcher (M159) ===
export async function createResearchBrief(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/research/briefs', jsonPost(payload)));
}

export async function executeResearch(briefId: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/research/execute', jsonPost({ brief_id: briefId })));
}

export async function fetchResearchScopes(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/research/scopes'));
}

// === Builder (M160) ===
export async function executeBuilderTask(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/builder/execute', jsonPost(payload)));
}

export async function fetchBuilderProposals(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/builder/proposals'));
}

// === SkillLearner (M162) ===
export async function autoScanSkillLearner(keyword: string = "", fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/skill-learner/auto-scan', jsonPost({ keyword })));
}

export async function recordFailure(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/skill-learner/failures', jsonPost(payload)));
}

// === Reviewer (M161) ===
export async function reviewBuilderOutput(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/reviewer/review', jsonPost(payload)));
}

export async function fetchReviewVerdictLabel(verdict: string, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`/reviewer/verdict/${encodeURIComponent(verdict)}`));
}

// === Orchestrator (M163) ===
export async function runOrchestrator(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/orchestrator/run', jsonPost(payload)));
}

export async function fetchOrchestratorRoles(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/orchestrator/roles'));
}

// === Sleep/Wake (M164) ===
export async function sleepAgent(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/sleep-wake/sleep', jsonPost(payload)));
}

export async function wakeAgent(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/sleep-wake/wake', jsonPost(payload)));
}

export async function fetchSleepWakeStatus(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/sleep-wake/status'));
}

// === Gate Freeze (M165) ===
export async function freezeGate(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/gate/freeze', jsonPost(payload)));
}

export async function unfreezeGate(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/gate/unfreeze', jsonPost({})));
}

export async function fetchGateStatus(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/gate/status'));
}

// === Tool Verification (M166) ===
export async function verifyTools(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/tools/verify'));
}

// === Self-Review Auto-Fix (M167) ===
export async function autoFixReviewFindings(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/reviewer/auto-fix', jsonPost(payload)));
}

// === Auto-Continue (M169) ===
export async function autoContinueOrchestration(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/orchestrator/auto-continue', jsonPost(payload)));
}

export async function fetchAutoContinueStatus(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/orchestrator/auto-continue/status'));
}

// === E2E Autonomous Loop (M170) ===
export async function runAutonomousLoop(payload: Record<string, unknown>, fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/orchestrator/autonomous-loop', jsonPost(payload)));
}

// === Desktop Beta Ship (M171-M180) ===
export async function fetchDesktopBetaShip(fetcher: Fetcher): Promise<Record<string, unknown>> {
  return readJson(await fetcher('/desktop/beta-ship'));
}

function jsonPost(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  return response.json() as Promise<T>;
}
