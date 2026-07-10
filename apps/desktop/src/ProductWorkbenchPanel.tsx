import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';

interface WorkbenchStage {
  stage_id: string;
  label_cn: string;
  status: string;
  detail_cn: string;
}

interface WorkbenchLane {
  lane_id: string;
  label_cn: string;
  status: string;
  detail_cn: string;
}

interface WorkbenchSnapshot {
  summary_cn: string;
  read_only: boolean;
  current_stage_id: string;
  stages: WorkbenchStage[];
  lanes: WorkbenchLane[];
  safety: {
    auto_apply_allowed: boolean;
    auto_approve_allowed: boolean;
    human_approval_required: boolean;
    dangerous_operations_blocked: boolean;
    summary_cn: string;
  };
  patch_approval?: {
    label_cn: string;
    warning_cn: string;
    checks: { check_id: string; label_cn: string; required: boolean; status: string }[];
  };
  test_feedback?: {
    label_cn: string;
    warning_cn: string;
    arbitrary_shell_allowed: boolean;
    commands: { test_id: string; label_cn: string; status: string }[];
  };
  failure_recovery?: {
    label_cn: string;
    warning_cn: string;
    auto_retry_allowed: boolean;
    auto_resume_allowed: boolean;
    checks: { check_id: string; label_cn: string; required: boolean; status: string }[];
  };
  next_actions: string[];
}

interface Props {
  api: {
    fetchProductWorkbench: () => Promise<WorkbenchSnapshot>;
  };
}

export function ProductWorkbenchPanel({ api }: Props) {
  const [data, setData] = useState<WorkbenchSnapshot | null>(null);
  const [error, setError] = useState('');
  const { fetchProductWorkbench } = api;

  useEffect(() => {
    let cancelled = false;
    fetchProductWorkbench()
      .then((next) => {
        if (!cancelled) setData(next);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => { cancelled = true; };
  }, [fetchProductWorkbench]);

  if (error) {
    return <section style={panelStyle}><p style={{ color: '#b91c1c' }}>加载 Agent 工作台失败：{error}</p></section>;
  }
  if (!data) {
    return <section style={panelStyle}><p style={{ color: '#6b7280' }}>加载 Agent 工作台中...</p></section>;
  }

  return (
    <section style={panelStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
        <div>
          <h2 style={titleStyle}>Agent 工作台</h2>
          <p style={summaryStyle}>{data.summary_cn}</p>
        </div>
        <span style={readonlyBadge}>{data.read_only ? '只读' : '可操作'}</span>
      </div>

      <div style={stageGridStyle}>
        {data.stages.map((stage, index) => (
          <div key={stage.stage_id} style={stageCardStyle(stage.status)}>
            <div style={stepStyle}>{index + 1}</div>
            <div>
              <div style={{ fontWeight: 700 }}>{stage.label_cn}</div>
              <div style={detailStyle}>{stage.detail_cn}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={laneGridStyle}>
        {data.lanes.map((lane) => (
          <div key={lane.lane_id} style={laneStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <strong>{lane.label_cn}</strong>
              <span style={laneBadgeStyle(lane.status)}>{statusLabel(lane.status)}</span>
            </div>
            <p style={detailStyle}>{lane.detail_cn}</p>
          </div>
        ))}
      </div>

      <div style={safetyStyle}>
        <strong>安全边界</strong>
        <p style={{ margin: '4px 0 0', color: '#78350f' }}>{data.safety.summary_cn}</p>
      </div>

      {data.patch_approval && (
        <div style={approvalStyle}>
          <strong>{data.patch_approval.label_cn}</strong>
          <p style={{ margin: '4px 0 8px', color: '#7c2d12' }}>{data.patch_approval.warning_cn}</p>
          <div style={{ display: 'grid', gap: 4 }}>
            {data.patch_approval.checks.map((check) => (
              <div key={check.check_id} style={checkStyle}>
                <span>{check.label_cn}</span>
                <span style={laneBadgeStyle(check.status)}>{statusLabel(check.status)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.test_feedback && (
        <div style={testStyle}>
          <strong>{data.test_feedback.label_cn}</strong>
          <p style={{ margin: '4px 0 8px', color: '#164e63' }}>{data.test_feedback.warning_cn}</p>
          <div style={commandGridStyle}>
            {data.test_feedback.commands.map((command) => (
              <div key={command.test_id} style={commandStyle}>
                <span>{command.label_cn}</span>
                <span style={laneBadgeStyle(command.status)}>{statusLabel(command.status)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.failure_recovery && (
        <div style={recoveryStyle}>
          <strong>{data.failure_recovery.label_cn}</strong>
          <p style={{ margin: '4px 0 8px', color: '#7f1d1d' }}>{data.failure_recovery.warning_cn}</p>
          <div style={{ display: 'grid', gap: 4 }}>
            {data.failure_recovery.checks.map((check) => (
              <div key={check.check_id} style={recoveryCheckStyle}>
                <span>{check.label_cn}</span>
                <span style={laneBadgeStyle(check.status)}>{statusLabel(check.status)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <strong style={{ fontSize: 13 }}>下一步</strong>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
          {data.next_actions.map((item) => <li key={item} style={detailStyle}>{item}</li>)}
        </ul>
      </div>
    </section>
  );
}

function statusLabel(status: string): string {
  if (status === 'active') return '当前';
  if (status === 'blocked') return '需批准';
  if (status === 'ready') return '就绪';
  return '暂无';
}

const panelStyle = {
  padding: '14px 16px',
  borderBottom: '1px solid #e5e7eb',
  fontSize: 13,
} satisfies CSSProperties;

const titleStyle = { margin: 0, fontSize: 18, fontWeight: 800 } satisfies CSSProperties;
const summaryStyle = { margin: '4px 0 0', color: '#4b5563', lineHeight: 1.45 } satisfies CSSProperties;
const readonlyBadge = { padding: '2px 8px', border: '1px solid #16a34a', borderRadius: 4, color: '#166534', background: '#f0fdf4' } satisfies CSSProperties;
const stageGridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, marginTop: 12 } satisfies CSSProperties;
const laneGridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8, marginTop: 12 } satisfies CSSProperties;
const detailStyle = { margin: '3px 0 0', color: '#6b7280', fontSize: 12, lineHeight: 1.4 } satisfies CSSProperties;
const stepStyle = { width: 22, height: 22, borderRadius: 4, background: '#111827', color: '#fff', display: 'grid', placeItems: 'center', flex: '0 0 auto', fontSize: 12 } satisfies CSSProperties;
const laneStyle = { border: '1px solid #e5e7eb', borderRadius: 6, padding: 10, background: '#fff' } satisfies CSSProperties;
const safetyStyle = { marginTop: 12, padding: 10, border: '1px solid #f59e0b', borderRadius: 6, background: '#fffbeb', fontSize: 12 } satisfies CSSProperties;
const approvalStyle = { marginTop: 12, padding: 10, border: '1px solid #fed7aa', borderRadius: 6, background: '#fff7ed', fontSize: 12 } satisfies CSSProperties;
const checkStyle = { display: 'flex', justifyContent: 'space-between', gap: 8, padding: '4px 0', borderTop: '1px solid #ffedd5' } satisfies CSSProperties;
const testStyle = { marginTop: 12, padding: 10, border: '1px solid #bae6fd', borderRadius: 6, background: '#f0f9ff', fontSize: 12 } satisfies CSSProperties;
const commandGridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 6 } satisfies CSSProperties;
const commandStyle = { display: 'flex', justifyContent: 'space-between', gap: 8, padding: 6, border: '1px solid #e0f2fe', borderRadius: 4, background: '#fff' } satisfies CSSProperties;
const recoveryStyle = { marginTop: 12, padding: 10, border: '1px solid #fecaca', borderRadius: 6, background: '#fef2f2', fontSize: 12 } satisfies CSSProperties;
const recoveryCheckStyle = { display: 'flex', justifyContent: 'space-between', gap: 8, padding: '4px 0', borderTop: '1px solid #fee2e2' } satisfies CSSProperties;

function stageCardStyle(status: string): CSSProperties {
  return {
    display: 'flex',
    gap: 8,
    minHeight: 76,
    padding: 10,
    borderRadius: 6,
    border: `1px solid ${status === 'blocked' ? '#f59e0b' : status === 'active' ? '#2563eb' : '#e5e7eb'}`,
    background: status === 'blocked' ? '#fffbeb' : status === 'active' ? '#eff6ff' : '#fff',
  };
}

function laneBadgeStyle(status: string): CSSProperties {
  return {
    alignSelf: 'flex-start',
    padding: '1px 6px',
    borderRadius: 4,
    fontSize: 11,
    background: status === 'ready' ? '#f0fdf4' : status === 'blocked' ? '#fffbeb' : '#f3f4f6',
    color: status === 'ready' ? '#166534' : status === 'blocked' ? '#92400e' : '#6b7280',
  };
}
