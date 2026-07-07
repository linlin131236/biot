import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ReleaseReadinessPanel } from './ReleaseReadinessPanel';

function fakeApi(data: { readiness?: Record<string, unknown>; checklist?: Record<string, unknown>; recovery?: Record<string, unknown> }) {
  return {
    fetchReleaseReadiness: vi.fn().mockResolvedValue(data.readiness || {}),
    fetchLocalChecklist: vi.fn().mockResolvedValue(data.checklist || { checks: [] }),
    fetchRecoveryPolicy: vi.fn().mockResolvedValue(data.recovery || {}),
  };
}

const readyData = {
  readiness: { ready: true },
  checklist: { checks: [{ label: 'Lint OK', passed: true }] },
  recovery: { summary_cn: '自动恢复策略就绪' },
};

const notReadyData = {
  readiness: { ready: false },
  checklist: { checks: [{ label: '测试未通过', passed: false, reason: '3 tests failed', suggestion: '修复测试' }] },
  recovery: { summary_cn: '' },
};

describe('ReleaseReadinessPanel', () => {
  it('renders loading', () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('shows ready state', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/已准备好发布/)).toBeTruthy());
  });

  it('shows not ready state', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(notReadyData)} />);
    await waitFor(() => expect(screen.getByText(/尚未准备好发布/)).toBeTruthy());
  });

  it('shows blocker reason', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(notReadyData)} />);
    await waitFor(() => expect(screen.getByText(/3 tests failed/)).toBeTruthy());
  });

  it('shows recovery summary', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/自动恢复策略就绪/)).toBeTruthy());
  });

  it('has read-only note', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
  });

  it('no release buttons', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy());
    const buttons = document.querySelectorAll('button');
    const texts = Array.from(buttons).map(b => b.textContent?.toLowerCase() || '');
    expect(texts.some(t => t.includes('release') || t.includes('push') || t.includes('tag'))).toBe(false);
  });
});
