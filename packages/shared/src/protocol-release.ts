/** Release readiness and checklist types. Split from protocol-autonomy.ts for size. */

export interface ReleaseReadinessCheck {
  code: string;
  label: string;
  passed: boolean;
  severity: 'blocking' | 'warning' | 'info';
  severity_label: '阻断' | '警告' | '提示';
  detail: string;
}

export interface ReleaseReadiness {
  ready: boolean;
  checks: ReleaseReadinessCheck[];
  blockers: string[];
  warnings: string[];
}

export interface LocalReleaseChecklistItem {
  code: string;
  category: string;
  label: string;
  status: 'pass' | 'fail' | 'warn';
  status_label: string;
  detail: string;
  recommendation: string | null;
}

export interface LocalReleaseChecklist {
  ready: boolean;
  items: LocalReleaseChecklistItem[];
  blockers: string[];
  warnings: string[];
  next_step: string;
  disclaimer: string;
}
