/** Task result summary types: structured closure outcome for frontend display. */

export interface TaskResultSummary {
  closure_id: string;
  status: string;
  steps: number;
  duration_seconds: number;
  changed_files: string[];
  commands: string[];
  command_results: string[];
  final_output: string | null;
  error: string | null;
  review_summary: string | null;
  next_action: string | null;
  retry_count: number;
  permission_requests: string[];
}
