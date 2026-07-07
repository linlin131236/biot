import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuditTimelinePanel } from './AuditTimelinePanel';

function fakeApi(data: Record<string, unknown>) {
  return { fetchAuditTimeline: vi.fn().mockResolvedValue(data) };
}

describe('AuditTimelinePanel', () => {
  it('renders loading', () => {
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events: [], total: 0 })} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('renders empty', async () => {
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/暂无审计事件/)).toBeTruthy());
  });

  it('renders events', async () => {
    const events = [{ id: 'e1', source: 'queue', label: '测试事件', summary: '详情', status: 'completed', occurred_at: 1234567890 }];
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events, total: 1 })} />);
    await waitFor(() => expect(screen.getByText('测试事件')).toBeTruthy());
  });

  it('shows Chinese labels', async () => {
    const events = [{ id: 'e1', source: 'queue', label: '事件', summary: '', status: 'completed', occurred_at: 1234567890 }];
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events, total: 1 })} />);
    await waitFor(() => expect(screen.getByText(/执行队列/)).toBeTruthy());
  });

  it('has read-only note', async () => {
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
  });

  it('no execute buttons', async () => {
    render(<AuditTimelinePanel baseUrl="http://t" api={fakeApi({ events: [], total: 0 })} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
    const buttons = document.querySelectorAll('button');
    expect(buttons.length).toBe(0);
  });
});
