type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function createAgentCoreFetcher(fetcher: Fetcher = fetch): Fetcher {
  return async (input: string, init?: RequestInit) => {
    const endpoint = await readAgentCoreEndpoint();
    if (typeof window !== 'undefined' && window.bolt?.agentCoreFetch && isTrustedAgentCoreUrl(input, endpoint.port)) {
      const response = await window.bolt.agentCoreFetch(input, serializeRequestInit(init));
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    return fetcher(input, init);
  };
}

function serializeRequestInit(init?: RequestInit): { method?: string; headers?: [string, string][]; body?: string } | undefined {
  if (!init) return undefined;
  if (init.body !== undefined && init.body !== null && typeof init.body !== 'string') {
    throw new Error('Agent Core 请求体必须是字符串');
  }
  return {
    method: init.method,
    headers: Array.from(new Headers(init.headers).entries()),
    body: typeof init.body === 'string' ? init.body : undefined,
  };
}

async function readAgentCoreEndpoint(): Promise<{ port: number }> {
  if (typeof window === 'undefined') return { port: 8000 };
  const endpoint = await window.bolt?.agentCoreEndpoint?.();
  return typeof endpoint?.port === 'number' ? endpoint : { port: 8000 };
}

function isTrustedAgentCoreUrl(input: string, allowedPort: number): boolean {
  try {
    const url = new URL(input);
    const port = url.port || (url.protocol === 'https:' ? '443' : '80');
    return (url.protocol === 'http:' || url.protocol === 'https:')
      && ['localhost', '127.0.0.1', '::1', '[::1]'].includes(url.hostname)
      && port === String(allowedPort);
  } catch {
    return false;
  }
}
