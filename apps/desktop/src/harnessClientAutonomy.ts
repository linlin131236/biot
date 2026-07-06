/** Autonomy API client methods: Goal, Conversation, VectorMemory, Skill, Delegation, Checkpoint.
 *  Split from harnessClient.ts to respect the 300-line size gate.
 */
import type {
  Goal, ConversationMessage, SkillManifest, DelegationTask,
  Checkpoint, ReviewChecklist, ReviewResult,
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
export async function steerRun(baseUrl: string, runId: string, content: string, fetcher: Fetcher = fetch): Promise<{ status: string }> {
  return readJson(await fetcher(`${baseUrl}/runs/${runId}/steering`, jsonPost({ content })));
}

export async function fetchRunTimeline(baseUrl: string, runId: string, fetcher: Fetcher = fetch): Promise<unknown[]> {
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
