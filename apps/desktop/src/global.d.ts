/**
 * Bolt Electron bridge type declarations.
 * These types are available when running inside the Electron desktop app.
 */

interface BoltBridge {
  selectWorkspace: () => Promise<string | null>;
  agentCoreAuth?: () => Promise<string | null> | string | null;
}

declare global {
  interface Window {
    bolt?: BoltBridge;
  }
}

export {};
