/**
 * Bolt Electron bridge type declarations.
 * These types are available when running inside the Electron desktop app.
 */

interface BoltBridge {
  selectWorkspace: () => Promise<string | null>;
  agentCoreEndpoint?: () => Promise<{ port: number }> | { port: number };
  agentCoreFetch?: (
    input: string,
    init?: {
      method?: string;
      headers?: Record<string, string> | [string, string][];
      body?: string;
    },
  ) => Promise<{
    status: number;
    statusText: string;
    headers: [string, string][];
    body: string;
  }>;
}

declare global {
  interface Window {
    bolt?: BoltBridge;
  }
}

export {};
