type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export function createAgentCoreFetcher(fetcher: Fetcher = fetch): Fetcher {
  return async (input: string, init?: RequestInit) => {
    const token = await readAgentCoreToken();
    if (!token) return fetcher(input, init);
    const headers = new Headers(init?.headers);
    if (!headers.has('authorization')) headers.set('authorization', `Bearer ${token}`);
    return fetcher(input, { ...init, headers });
  };
}

async function readAgentCoreToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  return window.bolt?.agentCoreAuth ? window.bolt.agentCoreAuth() : null;
}
