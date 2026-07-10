/**
 * Bolt Electron bridge type declarations.
 * These types are available when running inside the Electron desktop app.
 */

type AgentCoreIpcResponse = {
  requestId: string;
  generationId: string;
  status: number;
  statusText: string;
  headers: Array<[string, string]>;
  body: string;
};

type AgentCoreBridgeHandle = {
  requestId: string;
  response: Promise<AgentCoreIpcResponse>;
  cancel: () => Promise<'cancelled' | 'already_finished'>;
};

interface BoltBridge {
  selectWorkspace: () => Promise<string | null>;
  agentCoreRequest?: (
    input: string,
    init?: {
      method?: string;
      headers?: [string, string][];
      body?: string;
    },
  ) => AgentCoreBridgeHandle;
}

declare global {
  interface Window {
    bolt?: BoltBridge;
  }
}

export {};
