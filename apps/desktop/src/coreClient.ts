import type { CoreStatus } from './state';

type Fetcher = (input: string) => Promise<Response>;

export async function fetchCoreHealth(fetcher: Fetcher): Promise<CoreStatus> {
  try {
    const response = await fetcher('/health');
    const payload = await response.json();
    return payload.status === 'ok' ? 'ok' : 'down';
  } catch {
    return 'down';
  }
}
