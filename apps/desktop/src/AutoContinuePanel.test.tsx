/**
 * AutoContinuePanel tests (M169).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutoContinuePanel } from './AutoContinuePanel';

function apiFixture(statusData: Record<string, unknown> = { enabled: false }) {
  return {
    autoContinue: vi.fn().mockResolvedValue({ ...statusData, updated_at: new Date().toISOString() }),
    fetchAutoContinueStatus: vi.fn().mockResolvedValue(statusData),
  };
}

describe('AutoContinuePanel', () => {
  it('renders title', () => {
    render(<AutoContinuePanel api={apiFixture()} />);
    expect(screen.getByText('自动继续')).toBeTruthy();
  });

  it('shows disabled status initially', async () => {
    render(<AutoContinuePanel api={apiFixture()} />);
    expect(await screen.findByText('自动继续：已关闭')).toBeTruthy();
  });

  it('uses the provided authenticated fetcher', async () => {
    const api = apiFixture();
    const fetcher = vi.fn();
    render(<AutoContinuePanel fetcher={fetcher} api={api} />);
    await waitFor(() => expect(api.fetchAutoContinueStatus).toHaveBeenCalledWith(fetcher));
  });

  it('enables auto-continue', async () => {
    const api = apiFixture({ enabled: false });
    const fetcher = vi.fn();
    api.autoContinue.mockResolvedValueOnce({ enabled: true, updated_at: new Date().toISOString() });
    render(<AutoContinuePanel api={api} fetcher={fetcher} />);
    await screen.findByText('自动继续：已关闭');
    fireEvent.click(screen.getByRole('button', { name: '开启自动继续' }));
    await waitFor(() => expect(api.autoContinue).toHaveBeenCalledWith({ enabled: true }, fetcher));
    expect(await screen.findByText('自动继续：已开启')).toBeTruthy();
  });

  it('disables auto-continue', async () => {
    const api = apiFixture({ enabled: true });
    const fetcher = vi.fn();
    api.autoContinue.mockResolvedValueOnce({ enabled: false, updated_at: new Date().toISOString() });
    render(<AutoContinuePanel api={api} fetcher={fetcher} />);
    expect(await screen.findByText('自动继续：已开启')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '关闭自动继续' }));
    await waitFor(() => expect(api.autoContinue).toHaveBeenCalledWith({ enabled: false }, fetcher));
    expect(await screen.findByText('自动继续：已关闭')).toBeTruthy();
  });

  it('shows error on failure', async () => {
    const api = apiFixture();
    api.fetchAutoContinueStatus.mockRejectedValueOnce(new Error('加载失败'));
    render(<AutoContinuePanel api={api} />);
    expect(await screen.findByText('加载状态失败：加载失败')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<AutoContinuePanel api={apiFixture()} />);
    const dangerous = screen.queryAllByText(/push|release|tag|delete|destroy|kill/);
    expect(dangerous.length).toBe(0);
  });
});
