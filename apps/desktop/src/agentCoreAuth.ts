type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function createAgentCoreFetcher(fetcher: Fetcher = fetch): Fetcher {
  return async (input: string, init?: RequestInit) => {
    if (typeof window !== 'undefined' && window.bolt?.agentCoreFetch && isTrustedAgentCoreUrl(input)) {
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

function isTrustedAgentCoreUrl(input: string): boolean {
  try {
    const url = new URL(input);
    return (url.protocol === 'http:' || url.protocol === 'https:')
      && ['localhost', '127.0.0.1', '::1', '[::1]'].includes(url.hostname);
  } catch {
    return false;
  }
}
