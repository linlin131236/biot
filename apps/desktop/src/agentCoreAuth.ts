export type AgentCoreIpcResponse = {
  requestId: string;
  generationId: string;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: string;
};

export type AgentCoreRequestHandle = {
  requestId: string;
  response: Promise<Response>;
  cancel: () => Promise<'cancelled' | 'already_finished'>;
};

export type AgentCoreTransport = (
  input: string,
  init?: RequestInit,
) => AgentCoreRequestHandle;

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function createAgentCoreFetcher(): Fetcher {
  const transport = createAgentCoreTransport();
  return (input, init) => transport(input, init).response;
}

export function createAgentCoreTransport(): AgentCoreTransport {
  return (input: string, init?: RequestInit) => {
    const path = assertRelativeAgentCorePath(input);
    const bridge = typeof window === 'undefined' ? undefined : window.bolt?.agentCoreRequest;
    if (!bridge) {
      throw new Error('Bolt Desktop Agent Core bridge 不可用');
    }

    const handle = bridge(path, serializeRequestInit(init));
    return {
      requestId: handle.requestId,
      response: handle.response.then(toResponse),
      cancel: handle.cancel,
    };
  };
}

function assertRelativeAgentCorePath(input: string): string {
  if (typeof input !== 'string' || input.length === 0) {
    throw new Error('CORE_REQUEST_INVALID');
  }
  if (
    !input.startsWith('/')
    || input.startsWith('//')
    || input.includes('\\')
    || input.includes('#')
    || input.includes('://')
    || input.includes('@')
  ) {
    throw new Error('CORE_REQUEST_INVALID');
  }
  return input;
}

function toResponse(response: AgentCoreIpcResponse): Response {
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: response.headers,
  });
}

function serializeRequestInit(init?: RequestInit): { method?: string; headers?: [string, string][]; body?: string } | undefined {
  if (!init) return undefined;
  if (init.body !== undefined && init.body !== null && typeof init.body !== 'string') {
    throw new Error('Agent Core 请求体必须是字符串');
  }
  return {
    method: init.method,
    headers: init.headers ? Array.from(new Headers(init.headers).entries()) : undefined,
    body: typeof init.body === 'string' ? init.body : undefined,
  };
}
