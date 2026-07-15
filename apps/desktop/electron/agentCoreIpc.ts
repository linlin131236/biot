type IpcMainLike = {
  handle: (channel: string, handler: (event: IpcEventLike, payload: unknown) => Promise<unknown>) => void;
};

type IpcEventLike = {
  sender: { id: number };
};

type VerifiedGeneration = {
  generationId: string;
  endpoint: string;
  bearerToken: string;
};

type AgentCoreIpcDependencies = {
  getGeneration: () => VerifiedGeneration | null;
  isTrustedSender: (event: IpcEventLike) => boolean;
  fetch: typeof fetch;
};

type ActiveRequest = {
  ownerId: number;
  controller: AbortController;
};

const REQUEST_CHANNEL = 'bolt:agent-core:request';
const CANCEL_CHANNEL = 'bolt:agent-core:cancel';
const ALLOWED_HEADERS = new Set(['accept', 'content-type', 'if-match']);
const ALLOWED_METHODS = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);
const REQUEST_FIELDS = new Set(['requestId', 'path', 'method', 'headers', 'body', 'timeoutMs']);
const RESPONSE_HEADERS = new Set(['content-type', 'content-length', 'etag', 'retry-after', 'x-bolt-error-code']);
const MAX_RESPONSE_BYTES = 16 * 1024 * 1024;
const MAX_REQUEST_ID_LENGTH = 128;
const MAX_FINISHED_REQUESTS = 1024;

export function registerAgentCoreIpc(ipcMain: IpcMainLike, dependencies: AgentCoreIpcDependencies): void {
  const activeRequests = new Map<string, ActiveRequest>();
  const finishedRequests = new Map<string, number>();

  ipcMain.handle(REQUEST_CHANNEL, async (event, payload) => {
    if (!dependencies.isTrustedSender(event)) throw transportError('CORE_REQUEST_INVALID');
    const request = parseRequest(payload);
    const generation = dependencies.getGeneration();
    if (!generation) throw transportError('CORE_NOT_VERIFIED');
    if (activeRequests.has(request.requestId)) throw transportError('CORE_REQUEST_INVALID');

    const controller = new AbortController();
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, request.timeoutMs ?? 30_000);
    activeRequests.set(request.requestId, { ownerId: event.sender.id, controller });
    try {
      const headers = validateHeaders(request.headers);
      headers.set('authorization', `Bearer ${generation.bearerToken}`);
      const response = await dependencies.fetch(`${generation.endpoint}${request.path}`, {
        method: request.method,
        headers,
        body: request.body,
        signal: controller.signal,
        redirect: 'error',
      });
      assertCurrentGeneration(dependencies.getGeneration(), generation.generationId);
      if (response.headers.get('content-type')?.split(';', 1)[0].trim().toLowerCase() === 'text/event-stream') {
        controller.abort();
        throw transportError('CORE_STREAMING_UNSUPPORTED');
      }
      const body = await response.text();
      if (Buffer.byteLength(body, 'utf8') > MAX_RESPONSE_BYTES) throw transportError('CORE_RESPONSE_TOO_LARGE');
      assertCurrentGeneration(dependencies.getGeneration(), generation.generationId);
      return {
        requestId: request.requestId,
        generationId: generation.generationId,
        status: response.status,
        statusText: response.statusText,
        headers: Array.from(response.headers.entries()).filter(([name]) => RESPONSE_HEADERS.has(name.toLowerCase())),
        body,
      };
    } catch (error) {
      if (timedOut && !isTransportError(error)) throw transportError('CORE_TIMEOUT');
      if (controller.signal.aborted && !isTransportError(error)) {
        throw transportError('CORE_CANCELLED');
      }
      if (isTransportError(error)) throw error;
      throw error;
    } finally {
      clearTimeout(timeout);
      activeRequests.delete(request.requestId);
      rememberFinishedRequest(finishedRequests, request.requestId, event.sender.id);
    }
  });

  ipcMain.handle(CANCEL_CHANNEL, async (event, payload) => {
    if (!dependencies.isTrustedSender(event)) throw transportError('CORE_REQUEST_INVALID');
    const requestId = parseCancel(payload);
    const active = activeRequests.get(requestId);
    if (!active) {
      if (finishedRequests.get(requestId) === event.sender.id) return 'already_finished';
      throw transportError('CORE_REQUEST_INVALID');
    }
    if (active.ownerId !== event.sender.id) throw transportError('CORE_REQUEST_INVALID');
    active.controller.abort();
    return 'cancelled';
  });
}

function parseRequest(payload: unknown): {
  requestId: string;
  path: string;
  method: string;
  headers?: Array<[string, string]>;
  body?: string;
  timeoutMs?: number;
} {
  if (!isRecord(payload)
    || Object.keys(payload).some((key) => !REQUEST_FIELDS.has(key))
    || typeof payload.requestId !== 'string'
    || payload.requestId.length < 1
    || payload.requestId.length > MAX_REQUEST_ID_LENGTH
    || typeof payload.path !== 'string'
    || !isSafePath(payload.path)
    || typeof payload.method !== 'string'
    || (payload.headers !== undefined && !Array.isArray(payload.headers))
    || (payload.body !== undefined && typeof payload.body !== 'string')
    || (payload.timeoutMs !== undefined && (!Number.isInteger(payload.timeoutMs) || (payload.timeoutMs as number) < 1000 || (payload.timeoutMs as number) > 120000))
    || ((payload.method === 'GET' || payload.method === 'DELETE') && payload.body !== undefined)) {
    throw transportError('CORE_REQUEST_INVALID');
  }
  if (!ALLOWED_METHODS.has(payload.method)) throw transportError('CORE_METHOD_NOT_ALLOWED');
  return payload as ReturnType<typeof parseRequest>;
}

function rememberFinishedRequest(requests: Map<string, number>, requestId: string, ownerId: number): void {
  requests.set(requestId, ownerId);
  if (requests.size > MAX_FINISHED_REQUESTS) requests.delete(requests.keys().next().value!);
}

function parseCancel(payload: unknown): string {
  if (!isRecord(payload) || typeof payload.requestId !== 'string') {
    throw transportError('CORE_REQUEST_INVALID');
  }
  return payload.requestId;
}

function validateHeaders(entries: Array<[string, string]> | undefined): Headers {
  const headers = new Headers();
  for (const entry of entries ?? []) {
    if (!Array.isArray(entry) || entry.length !== 2 || typeof entry[0] !== 'string' || typeof entry[1] !== 'string') {
      throw transportError('CORE_REQUEST_INVALID');
    }
    const name = entry[0];
    if (name !== name.toLowerCase() || !ALLOWED_HEADERS.has(name)) throw transportError('CORE_HEADER_NOT_ALLOWED');
    if (name === 'accept' && !['application/json', 'text/plain'].includes(entry[1])) {
      throw transportError('CORE_HEADER_NOT_ALLOWED');
    }
    if (name === 'content-type' && !/^application\/json(?:;\s*charset=utf-8)?$/i.test(entry[1])) {
      throw transportError('CORE_HEADER_NOT_ALLOWED');
    }
    headers.append(name, entry[1]);
  }
  return headers;
}

function isSafePath(path: string): boolean {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('\\') || path.includes('#')) return false;
  if (/[%](?:2f|5c|00)/i.test(path) || /[\u0000-\u001f\u007f]/.test(path)) return false;
  try {
    const url = new URL(path, 'http://127.0.0.1');
    return url.origin === 'http://127.0.0.1' && `${url.pathname}${url.search}` === path;
  } catch {
    return false;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function assertCurrentGeneration(generation: VerifiedGeneration | null, expectedId: string): void {
  if (!generation || generation.generationId !== expectedId) throw transportError('CORE_RESTARTED');
}

function isTransportError(error: unknown): error is Error & { code: string } {
  if (!(error instanceof Error)) return false;
  const code = (error as Error & { code?: unknown }).code;
  return typeof code === 'string' && code.startsWith('CORE_');
}

function transportError(code: string): Error & { code: string } {
  return Object.assign(new Error(code), { code });
}
