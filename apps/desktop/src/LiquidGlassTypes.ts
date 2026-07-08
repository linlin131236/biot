import type { ReactNode } from 'react';
import type { DesktopSettingsStatus } from './LiquidGlassSettingsData';

export type Fetcher = (input: string, init?: RequestInit) => Promise<Response>;

export type ThemeMode = 'dark' | 'light';
export type ViewMode = 'home' | 'settings';

export interface LiquidGlassWorkbenchProps {
  workspacePath: string;
  coreStatus: string;
  runId: string | null;
  goal: string;
  setGoal: (value: string) => void;
  hasWorkspace: boolean;
  startRun: () => void;
  createGoal: () => void;
  runStep: () => void;
  refreshTrace: () => void;
  refreshMemory: () => void;
  refreshPermissions: () => void;
  runGardener: () => void;
  fetchTimeline: () => void;
  runReview: () => void;
  changeWorkspace: () => void;
  addWorkspaceToHistory: (baseUrl: string, path: string, fetcher: Fetcher) => Promise<void>;
  loadRecentSessions: (baseUrl: string, limit: number, fetcher: Fetcher) => Promise<RecentSession[]>;
  error?: ReactNode;
  toolFlow?: ReactNode;
  modelPanel?: ReactNode;
  legacyPanels: ReactNode;
  theme: ThemeMode;
  setTheme: (value: ThemeMode) => void;
  onSaveTheme: (next: ThemeMode) => void;
  settings: DesktopSettingsStatus | null;
  coreUrl: string;
  fetcher: Fetcher;
}

export type RecentSession = {
  id: string;
  title: string;
  time: string;
  status: string;
};

export interface LiquidGlassHomeProps {
  goal: string;
  setGoal: (value: string) => void;
  hasWorkspace: boolean;
  startRun: () => void;
  createGoal: () => void;
  runStep: () => void;
  refreshTrace: () => void;
  refreshMemory: () => void;
  refreshPermissions: () => void;
  runGardener: () => void;
  fetchTimeline: () => void;
  runReview: () => void;
  workspacePath: string;
  coreStatus: string;
  runId: string | null;
  error?: ReactNode;
  toolFlow?: ReactNode;
  modelPanel?: ReactNode;
  legacyPanels: ReactNode;
}
