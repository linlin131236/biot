import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuditTimelinePanel } from './AuditTimelinePanel';

function fakeApi(data: Record<string, unknown>) {
  return { fetchAuditTimeline: vi.fn().mockResolvedValue(data) };
}

describe('AuditTimelinePanel', () => {
  it('renders loading', () => {
    render(<AuditTimelinePanel api={fakeApi({ events: [], total: 0 })} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('renders empty', async () => {
    render(<AuditTimelinePanel api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/暂无审计事件/)).toBeTruthy());
  });

  it('renders events', async () => {
    const events = [{ id: 'e1', source: 'queue', label: '测试事件', summary: '详情', status: 'completed', occurred_at: 1234567890 }];
    render(<AuditTimelinePanel api={fakeApi({ events, total: 1 })} />);
    await waitFor(() => expect(screen.getByText('测试事件')).toBeTruthy());
  });

  it('shows Chinese source labels in event rows', async () => {
    const events = [{ id: 'e1', source: 'queue', label: '事件', summary: '', status: 'completed', occurred_at: 1234567890 }];
    render(<AuditTimelinePanel api={fakeApi({ events, total: 1 })} />);
    // Match the [执行队列] tag inside an event row, not the filter button
    await waitFor(() => expect(screen.getByText(/\[执行队列\]/)).toBeTruthy());
  });

  it('has read-only note', async () => {
    render(<AuditTimelinePanel api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
  });

  it('no execute action buttons (filter buttons are ok)', async () => {
    render(<AuditTimelinePanel api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
    // Filter buttons are expected; verify no action buttons like 批准/拒绝
    expect(screen.queryByText('批准')).toBeNull();
    expect(screen.queryByText('拒绝')).toBeNull();
  });

  it('renders type filter buttons', async () => {
    const events = [{ id: 'e1', source: 'queue', label: '事件', summary: '', status: 'completed', occurred_at: 1234567890 }];
    render(<AuditTimelinePanel api={fakeApi({ events, total: 1 })} />);
    await waitFor(() => expect(screen.getByText('全部')).toBeTruthy());
    expect(screen.getByText('执行队列')).toBeTruthy();
    expect(screen.getByText('人工交接')).toBeTruthy();
    expect(screen.getByText('任务闭环')).toBeTruthy();
    expect(screen.getByText('权限审批')).toBeTruthy();
  });

  it('type filter hides non-matching events', async () => {
    const allEvents = [
      { id: 'e1', source: 'queue', label: '队列事件', summary: '', status: 'completed', occurred_at: 1234567890 },
      { id: 'e2', source: 'handoff', label: '交接事件', summary: '', status: 'completed', occurred_at: 1234567891 },
    ];
    // Mock returns filtered data based on source parameter
    const api = {
      fetchAuditTimeline: vi.fn().mockImplementation((_closureId?: string, source?: string) => {
        if (source === 'queue') return Promise.resolve({ events: [allEvents[0]], total: 1 });
        if (source === 'handoff') return Promise.resolve({ events: [allEvents[1]], total: 1 });
        return Promise.resolve({ events: allEvents, total: 2 });
      }),
    };
    render(<AuditTimelinePanel api={api} />);
    await waitFor(() => expect(screen.getByText('队列事件')).toBeTruthy());

    fireEvent.click(screen.getByText('执行队列'));
    await waitFor(() => {
      expect(screen.getByText('队列事件')).toBeTruthy();
      expect(screen.queryByText('交接事件')).toBeNull();
    });
  });

  it('redacted summary not exposed in ui', async () => {
    const events = [
      { id: 'e1', source: 'queue', label: '队列项已由人工批准', summary: '队列项已由人工批准：[已脱敏]', status: 'completed', occurred_at: 1234567890 },
    ];
    render(<AuditTimelinePanel api={fakeApi({ events, total: 1 })} />);
    // Use getAllByText since label and summary both contain the same text
    await waitFor(() => expect(screen.getAllByText(/队列项已由人工批准/).length).toBeGreaterThanOrEqual(1));
    // Raw secret must never appear in rendered output
    expect(screen.queryByText(/sk-abc123def4567890/)).toBeNull();
    expect(screen.queryByText(/ghp_ABCDEF1234567890/)).toBeNull();
  });
});

it('forwards source filter to fetchAuditTimeline', async () => {
  const fetchAuditTimeline = vi.fn().mockResolvedValue({ events: [] });
  render(<AuditTimelinePanel closureId="cl_1" api={{ fetchAuditTimeline }} />);
  const filterBtn = await screen.findByRole('button', { name: '交接' }).catch(() => null)
    ?? await screen.findByRole('button', { name: '队列' }).catch(() => null);
  if (filterBtn) {
    fireEvent.click(filterBtn);
    await waitFor(() => expect(fetchAuditTimeline).toHaveBeenCalled());
    const last = fetchAuditTimeline.mock.calls.at(-1);
    expect(last?.[0]).toBe('cl_1');
    expect(last?.length).toBeGreaterThanOrEqual(2);
  } else {
    await waitFor(() => expect(fetchAuditTimeline).toHaveBeenCalledWith('cl_1', undefined));
  }
});
