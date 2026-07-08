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
export async function createGoal(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher = fetch): Promise<Goal> {
  return readJson(await fetcher(`${baseUrl}/goals`, jsonPost(payload)));
}

export async function getGoal(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<Goal> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}`));
}

export async function pauseGoal(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<Goal> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}/pause`, { method: 'POST' }));
}

export async function resumeGoal(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<Goal> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}/resume`, { method: 'POST' }));
}

export async function fetchUnfinishedGoals(baseUrl: string, fetcher: Fetcher = fetch): Promise<Goal[]> {
  return readJson(await fetcher(`${baseUrl}/goals/unfinished`));
}

export async function clearGoal(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<Goal> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}/clear`, { method: 'POST' }));
}

export async function fetchGoalEvidence(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<GoalEvidence[]> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}/evidence`));
}

export async function fetchGoalBudget(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/goals/${goalId}/budget`));
}

// Re-export the typed runAgentLoop from harnessClient (uses jsonPost with content-type header).
export { runAgentLoop } from './harnessClient';

// === Conversation API ===
export async function createConversation(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher = fetch): Promise<{ id: string }> {
  return readJson(await fetcher(`${baseUrl}/conversations`, jsonPost(payload)));
}

export async function listConversations(baseUrl: string, fetcher: Fetcher = fetch): Promise<string[]> {
  return readJson(await fetcher(`${baseUrl}/conversations`));
}

export async function getConversation(baseUrl: string, conversationId: string, fetcher: Fetcher = fetch): Promise<ConversationMessage[]> {
  return readJson(await fetcher(`${baseUrl}/conversations/${conversationId}`));
}

export async function addMessage(baseUrl: string, conversationId: string, payload: Record<string, unknown>, fetcher: Fetcher = fetch): Promise<{ status: string }> {
  return readJson(await fetcher(`${baseUrl}/conversations/${conversationId}/messages`, jsonPost(payload)));
}

// === Timeline / Steering ===
export async function steerRun(baseUrl: string, runId: string, content: string, fetcher: Fetcher = fetch): Promise<SteeringResult> {
  return readJson(await fetcher(`${baseUrl}/runs/${runId}/steering`, jsonPost({ content })));
}

export async function fetchRunTimeline(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<TimelineEvent[]> {
  return readJson(await fetcher(`${baseUrl}/runs/${runId}/timeline`));
}

// === Skill API (read-only via harness) ===
export async function fetchSkills(baseUrl: string, fetcher: Fetcher = fetch): Promise<SkillManifest[]> {
  // NOT WIRED: backend has no /skills route yet
  throw new Error("Not implemented: /skills endpoint not registered in app.py");
}

// === Checkpoint API ===
export async function createCheckpoint(baseUrl: string, payload: Record<string, unknown>, fetcher: Fetcher = fetch): Promise<Checkpoint> {
  return readJson(await fetcher(`${baseUrl}/checkpoints`, jsonPost(payload)));
}

export async function loadCheckpoint(baseUrl: string, cpId: string, fetcher: Fetcher = fetch): Promise<Checkpoint | null> {
  return readJson(await fetcher(`${baseUrl}/checkpoints/${cpId}`));
}

// === Task Closure API ===
export async function fetchTaskTemplates(baseUrl: string, fetcher: Fetcher = fetch): Promise<TaskTemplate[]> {
  return readJson(await fetcher(`${baseUrl}/task-closures/templates`));
}

export async function createTaskClosure(baseUrl: string, payload: { objective: string; template_id: string; run_id?: string; goal_id?: string }, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures`, jsonPost(payload)));
}

export async function getTaskClosure(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}`));
}

export async function bindTaskClosureRun(baseUrl: string, closureId: string, runId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/bind-run`, jsonPost({ run_id: runId })));
}

export async function bindTaskClosureGoal(baseUrl: string, closureId: string, goalId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/bind-goal`, jsonPost({ goal_id: goalId })));
}

export async function getTaskClosureByRun(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/by-run/${runId}`));
}

export async function getTaskClosureByGoal(baseUrl: string, goalId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/by-goal/${goalId}`));
}

export async function addClosureEvent(baseUrl: string, closureId: string, payload: Record<string, unknown>, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/events`, jsonPost(payload)));
}

export async function addClosureReview(baseUrl: string, closureId: string, payload: { summary: string; passed: boolean }, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/review`, jsonPost(payload)));
}

export async function fetchTaskClosureVerificationPlan(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<VerificationPlan> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/verification-plan`));
}

export async function fetchTaskClosureAssessment(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<VerificationAssessment> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/assessment`));
}

export async function updateTaskClosureAssessment(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<TaskClosureEvidence> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/assessment`, jsonPost({})));
}

export async function fetchExecutionQueue(baseUrl: string, closureId?: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`${baseUrl}/execution-queue${query}`));
}

export async function proposeExecutionQueue(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem[]> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${closureId}/execution-queue/propose`, jsonPost({})));
}

export async function approveExecutionQueueItem(baseUrl: string, itemId: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`${baseUrl}/execution-queue/${itemId}/approve`, jsonPost({})));
}

export async function rejectExecutionQueueItem(baseUrl: string, itemId: string, reason: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`${baseUrl}/execution-queue/${itemId}/reject`, jsonPost({ reason })));
}

export async function completeExecutionQueueItem(baseUrl: string, itemId: string, result: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`${baseUrl}/execution-queue/${itemId}/complete`, jsonPost({ result })));
}

export async function failExecutionQueueItem(baseUrl: string, itemId: string, result: string, fetcher: Fetcher = fetch): Promise<ExecutionQueueItem> {
  return readJson(await fetcher(`${baseUrl}/execution-queue/${itemId}/fail`, jsonPost({ result })));
}

export async function fetchExecutionHandoffs(baseUrl: string, closureId?: string, fetcher: Fetcher = fetch): Promise<ExecutionHandoffRecord[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`${baseUrl}/execution-handoffs${query}`));
}

export async function createExecutionHandoff(baseUrl: string, itemId: string, fetcher: Fetcher = fetch): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`${baseUrl}/execution-queue/${itemId}/handoff`, jsonPost({})));
}

export async function completeExecutionHandoff(baseUrl: string, handoffId: string, result: string, fetcher: Fetcher = fetch): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`${baseUrl}/execution-handoffs/${handoffId}/complete`, jsonPost({ result })));
}

export async function failExecutionHandoff(baseUrl: string, handoffId: string, result: string, fetcher: Fetcher = fetch): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`${baseUrl}/execution-handoffs/${handoffId}/fail`, jsonPost({ result })));
}

export async function requestExecutionHandoffPermission(baseUrl: string, handoffId: string, fetcher: Fetcher = fetch): Promise<ExecutionHandoffRecord> {
  return readJson(await fetcher(`${baseUrl}/execution-handoffs/${handoffId}/request-permission`, jsonPost({})));
}

export async function fetchExecutionAuditTimeline(baseUrl: string, closureId: string, fetcher: Fetcher = fetch): Promise<ExecutionAuditTimelineEvent[]> {
  return readJson(await fetcher(`${baseUrl}/task-closures/${encodeURIComponent(closureId)}/execution-audit-timeline`));
}

export async function fetchExecutionAuditDiagnostics(baseUrl: string, closureId?: string, fetcher: Fetcher = fetch): Promise<ExecutionAuditDiagnostic[]> {
  const query = closureId ? `?closure_id=${encodeURIComponent(closureId)}` : '';
  return readJson(await fetcher(`${baseUrl}/execution-audit/diagnostics${query}`));
}

export async function fetchExecutionAuditIntegrity(baseUrl: string, fetcher: Fetcher = fetch): Promise<ExecutionAuditIntegrity[]> {
  return readJson(await fetcher(`${baseUrl}/execution-audit/integrity`));
}

export async function fetchReleaseReadiness(baseUrl: string, fetcher: Fetcher = fetch): Promise<ReleaseReadiness> {
  return readJson(await fetcher(`${baseUrl}/release-readiness`));
}

export async function fetchLocalReleaseChecklist(baseUrl: string, fetcher: Fetcher = fetch): Promise<LocalReleaseChecklist> {
  return readJson(await fetcher(`${baseUrl}/local-release-checklist`));
}

export async function fetchRecoveryPolicy(baseUrl: string, fetcher: Fetcher = fetch): Promise<RecoveryPolicy> {
  return readJson(await fetcher(`${baseUrl}/recovery-policy`));
}

// === Planner Task Graph API (M61) ===
export async function fetchPlannerGraphs(baseUrl: string, fetcher: Fetcher = fetch): Promise<TaskGraphSummary[]> {
  return readJson(await fetcher(`${baseUrl}/planner/graphs`));
}

export async function createPlannerGraph(baseUrl: string, payload: { title: string; objective: string }, fetcher: Fetcher = fetch): Promise<TaskGraph> {
  return readJson(await fetcher(`${baseUrl}/planner/graphs`, jsonPost(payload)));
}

export async function fetchPlannerGraph(baseUrl: string, graphId: string, fetcher: Fetcher = fetch): Promise<TaskGraph> {
  return readJson(await fetcher(`${baseUrl}/planner/graphs/${graphId}`));
}

export async function addPlannerNode(baseUrl: string, graphId: string, payload: { title: string; dependencies?: string[]; risk?: string; owner_role?: string; evidence_refs?: string[] }, fetcher: Fetcher = fetch): Promise<TaskNode> {
  return readJson(await fetcher(`${baseUrl}/planner/graphs/${graphId}/nodes`, jsonPost(payload)));
}

export async function updatePlannerNodeStatus(baseUrl: string, graphId: string, nodeId: string, status: string, fetcher: Fetcher = fetch): Promise<TaskNode> {
  return readJson(await fetcher(`${baseUrl}/planner/graphs/${graphId}/nodes/${nodeId}`, jsonPost({ status })));
}

// === Execution State Machine API (M62) ===
export async function fetchStateMachineSummary(baseUrl: string, fetcher: Fetcher = fetch): Promise<StateMachineSummary> {
  return readJson(await fetcher(`${baseUrl}/execution/state-machine/summary`));
}

export async function validateTransition(baseUrl: string, payload: { from_state: string; to_state: string; node_id?: string; reason?: string }, fetcher: Fetcher = fetch): Promise<TransitionResult> {
  return readJson(await fetcher(`${baseUrl}/execution/state-machine/validate`, jsonPost(payload)));
}

// === Review Gate ===
export async function evaluateReview(baseUrl: string, payload: { items: string[]; results: Record<string, boolean> }, fetcher: Fetcher = fetch): Promise<ReviewResult> {
  return readJson(await fetcher(`${baseUrl}/review/evaluate`, jsonPost(payload)));
}

// === Memory Search (M79) ===
export async function fetchMemoryDecisions(baseUrl: string, keyword: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`${baseUrl}/decisions/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchMemoryFailures(baseUrl: string, keyword: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`${baseUrl}/failures/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchMemoryPreferences(baseUrl: string, keyword: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`${baseUrl}/preferences/query/by-keyword?keyword=${encodeURIComponent(keyword)}`));
}
export async function fetchProjectProfile(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/project/profile`));
}
export async function fetchCodeMapEntries(baseUrl: string, keyword: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`${baseUrl}/code-map/query?keyword=${encodeURIComponent(keyword)}`));
}

// === Multi-Agent Status (M87) ===
export async function fetchMultiAgentRoles(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  return readJson(await fetcher(`${baseUrl}/roles`));
}
export async function fetchSubtasksBoard(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/subtasks/board/summary`));
}
export async function fetchSubtasks(baseUrl: string, role?: string, status?: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>[]> {
  const params = new URLSearchParams();
  if (role) params.set('role', role);
  if (status) params.set('status', status);
  return readJson(await fetcher(`${baseUrl}/subtasks?${params.toString()}`));
}

// === Task Home (M91) ===
export async function fetchTaskHome(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/task-home`));
}

// === Permission Center (M92) ===
export async function fetchPermissionCenter(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/permission-center`));
}

export async function approvePermissionFromCenter(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/permissions/${requestId}/approve`, { method: 'POST' }));
}

export async function rejectPermissionFromCenter(baseUrl: string, requestId: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/permissions/${requestId}/reject`, { method: 'POST' }));
}

// === Audit Timeline (M93) ===
export async function fetchAuditTimeline(baseUrl: string, closureId?: string, source?: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (closureId) params.set("closure_id", closureId);
  if (source) params.set("source", source);
  const qs = params.toString();
  return readJson(await fetcher(`${baseUrl}/audit-timeline${qs ? `?${qs}` : ""}`));
}

// === Diagnostics Center (M94) ===
export async function fetchDiagnosticsCenter(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/diagnostics-center`));
}

// === Multi Task Queue (M96) ===
export async function fetchMultiTaskQueue(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/multi-task-queue`));
}

// === Failure Explanation (M97) ===
export async function fetchFailureExplanation(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/failure-explanation`));
}

// === Session Recovery (M98) ===
export async function fetchSessionRecovery(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/session-recovery`));
}

// === Settings Tools (M99) ===
export async function fetchSettingsTools(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/settings-tools`));
}

// === Patch Proposal (M107) ===
export async function fetchPatchList(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/tools/patch/list`));
}

export async function fetchPatchPreview(baseUrl: string, patchId: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/tools/patch/${patchId}/preview`));
}

// === Product Workbench (M126) ===
export async function fetchProductWorkbench(baseUrl: string, fetcher: Fetcher = fetch): Promise<Record<string, unknown>> {
  return readJson(await fetcher(`${baseUrl}/product-workbench`));
}

function jsonPost(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  return response.json() as Promise<T>;
}
