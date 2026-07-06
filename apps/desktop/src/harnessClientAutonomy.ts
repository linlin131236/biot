/** Autonomy API client methods: Goal, Conversation, Vector Memory, Skill, Delegation, Checkpoint.
 *  Split from harnessClient.ts to respect the 300-line size gate.
 */
import type {
  Goal, ConversationMessage, SkillManifest, DelegationTask,
  Checkpoint, ReviewChecklist, ReviewResult,
  TimelineEvent, GoalEvidence, SteeringResult,
  TaskTemplate, TaskClosureEvidence,
} from '@bolt/shared/autonomy';

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

// === Review Gate ===
export async function evaluateReview(baseUrl: string, payload: { items: string[]; results: Record<string, boolean> }, fetcher: Fetcher = fetch): Promise<ReviewResult> {
  return readJson(await fetcher(`${baseUrl}/review/evaluate`, jsonPost(payload)));
}

function jsonPost(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Agent Core request failed: ${response.status} ${response.statusText}`.trim());
  return response.json() as Promise<T>;
}
