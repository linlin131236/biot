/**
 * TaskResultSummaryPanel — 结果摘要展示 (M158).
 * 纯只读 UI，不访问 fs/shell/process/ipcRenderer。
 */
import type { TaskResultSummary } from '@bolt/shared/closure-summary';

interface Props {
  summary: TaskResultSummary | null;
  loading: boolean;
}

function summaryValue(value: unknown, fallback: string): string {
  if (value == null) return fallback;
  if (Array.isArray(value)) return value.length > 0 ? value.join(', ') : fallback;
  return String(value);
}

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}毫秒`;
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}分${s}秒`;
}

export function TaskResultSummaryPanel({ summary, loading }: Props) {
  if (loading) return <div style={{ padding: '0.5rem', color: '#a9bbca' }}>加载中…</div>;
  if (summary == null) return null;

  return (
    <div style={{ padding: '0.75rem', border: '1px solid #333', borderRadius: '0.25rem', marginTop: '0.5rem' }}>
      <strong style={{ display: 'block', marginBottom: '0.5rem' }}>结果摘要</strong>
      <div style={{ display: 'grid', gap: '0.25rem' }}>
        <div><strong>状态：</strong>{summaryValue(summary.status, '-')}</div>
        <div><strong>步数：</strong>{summaryValue(summary.steps, '-')}</div>
        <div><strong>耗时：</strong>{formatDuration(summary.duration_seconds)}</div>
        <div><strong>变更文件：</strong>{summaryValue(summary.changed_files, '无')}</div>
        <div>
          <strong>命令执行结果：</strong>
          {(summary.command_results ?? []).length > 0 ? (
            <div style={{ marginTop: '0.25rem' }}>
              {(summary.command_results ?? []).map((item, idx) => (
                <div key={idx} style={{ fontSize: '0.85rem', color: '#a9bbca' }}>{item}</div>
              ))}
            </div>
          ) : <span>无</span>}
        </div>
        {summary.error ? <div style={{ color: '#ff6f91' }}><strong>错误信息：</strong>{summary.error}</div> : null}
        {summary.review_summary ? <div><strong>审查摘要：</strong>{summary.review_summary}</div> : null}
        {summary.next_action ? <div><strong>下一步建议：</strong>{summary.next_action}</div> : null}
      </div>
    </div>
  );
}
