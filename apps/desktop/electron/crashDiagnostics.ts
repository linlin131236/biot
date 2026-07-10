import type { DiagnosticsStore } from './diagnosticsStore.js';

export type CrashLikeDetails = {
  reason?: string;
  exitCode?: number;
};

export function recordRendererGone(store: DiagnosticsStore | null | undefined, details?: CrashLikeDetails) {
  return store?.record({
    component: 'renderer',
    message: 'Renderer process gone',
    details: { reason: details?.reason, exitCode: details?.exitCode },
  }) ?? null;
}

export function recordMainException(store: DiagnosticsStore | null | undefined, error: unknown) {
  return store?.record({
    component: 'main',
    message: error instanceof Error ? error.message : 'uncaughtException',
    details: { name: error instanceof Error ? error.name : 'Error' },
  }) ?? null;
}

export function recordStartupFailure(store: DiagnosticsStore | null | undefined, errorMessage: string) {
  return store?.record({
    component: 'startup',
    message: errorMessage,
  }) ?? null;
}
