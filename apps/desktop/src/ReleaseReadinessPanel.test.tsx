import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ReleaseReadinessPanel } from './ReleaseReadinessPanel';

function fakeApi(data: { readiness?: Record<string, unknown>; checklist?: Record<string, unknown>; recovery?: Record<string, unknown> }) {
  return {
    fetchReleaseReadiness: vi.fn().mockResolvedValue(data.readiness || {}),
    fetchLocalChecklist: vi.fn().mockResolvedValue(data.checklist || { items: [] }),
    fetchRecoveryPolicy: vi.fn().mockResolvedValue(data.recovery || {}),
  };
}

const readyData = {
  readiness: { ready: true },
  checklist: { items: [{ label: 'Lint OK', status: 'pass', detail: 'ok' }] },
  recovery: { total: 10, disclaimer: '恢复策略只读参考' },
};

const notReadyData = {
  readiness: { ready: false },
  checklist: { items: [{ label: '测试未通过', status: 'fail', detail: '3 tests failed', recommendation: '修复测试' }] },
  recovery: { disclaimer: '' },
};

describe('ReleaseReadinessPanel', () => {
  it('renders loading', () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    expect(screen.getByText('加载中...')).toBeTruthy();
  });

  it('shows ready state', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/已准备好发布/)).toBeTruthy());
  });

  it('shows not ready state', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(notReadyData)} />);
    await waitFor(() => expect(screen.getByText(/尚未准备好发布/)).toBeTruthy());
  });

  it('shows blocker reason and recommendation from checklist items', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(notReadyData)} />);
    await waitFor(() => expect(screen.getByText(/3 tests failed/)).toBeTruthy());
    expect(screen.getByText(/修复测试/)).toBeTruthy();
  });

  it('supports legacy checks shape', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi({
      readiness: { ready: false },
      checklist: { checks: [{ label: 'legacy', passed: false, reason: 'old reason', suggestion: 'old suggestion' }] },
    })} />);
    await waitFor(() => expect(screen.getByText(/old reason/)).toBeTruthy());
    expect(screen.getByText(/old suggestion/)).toBeTruthy();
  });

  it('shows recovery summary', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/恢复策略只读参考/)).toBeTruthy());
  });

  it('has read-only note', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/只读发布准备检查/)).toBeTruthy());
  });

  it('no release buttons', async () => {
    render(<ReleaseReadinessPanel baseUrl="http://t" api={fakeApi(readyData)} />);
    await waitFor(() => expect(screen.getByText(/只读发布准备检查/)).toBeTruthy());
    const buttons = document.querySelectorAll('button');
    const texts = Array.from(buttons).map((button) => button.textContent?.toLowerCase() || '');
    expect(texts.some((text) => text.includes('release') || text.includes('push') || text.includes('tag'))).toBe(false);
  });
});
