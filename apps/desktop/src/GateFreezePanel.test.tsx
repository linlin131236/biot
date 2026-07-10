/**
 * GateFreezePanel tests (M165).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { GateFreezePanel } from './GateFreezePanel';

function apiFixture(statusData: Record<string, unknown> = { frozen: false }) {
  return {
    freezeGate: vi.fn().mockResolvedValue({ ...statusData, frozen: true }),
    unfreezeGate: vi.fn().mockResolvedValue({ frozen: false }),
    fetchGateStatus: vi.fn().mockResolvedValue(statusData),
  };
}

describe('GateFreezePanel', () => {
  it('renders title', () => {
    render(<GateFreezePanel api={apiFixture()} />);
    expect(screen.getByText('Gate 冻结控制')).toBeTruthy();
  });

  it('shows unfrozen status initially', async () => {
    render(<GateFreezePanel api={apiFixture()} />);
    expect(await screen.findByText('当前状态：未冻结')).toBeTruthy();
  });

  it('uses the provided authenticated fetcher', async () => {
    const api = apiFixture();
    const fetcher = vi.fn();
    render(<GateFreezePanel fetcher={fetcher} api={api} />);
    await waitFor(() => expect(api.fetchGateStatus).toHaveBeenCalledWith(fetcher));
  });

  it('freezes gate and shows frozen state', async () => {
    const api = apiFixture({ frozen: false });
    render(<GateFreezePanel api={api} />);
    await screen.findByText('当前状态：未冻结');
    fireEvent.change(screen.getByPlaceholderText('冻结原因'), { target: { value: '维护' } });
    fireEvent.click(screen.getByRole('button', { name: '冻结 Gate' }));
    await waitFor(() => expect(api.freezeGate).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：已冻结')).toBeTruthy();
  });

  it('unfreezes gate', async () => {
    const api = apiFixture({ frozen: true, reason: '维护' });
    render(<GateFreezePanel api={api} />);
    expect(await screen.findByText('当前状态：已冻结')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: '解冻 Gate' }));
    await waitFor(() => expect(api.unfreezeGate).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：未冻结')).toBeTruthy();
  });

  it('shows reason when frozen', async () => {
    const api = apiFixture({ frozen: true, reason: '系统升级' });
    render(<GateFreezePanel api={api} />);
    expect(await screen.findByText('原因：系统升级')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<GateFreezePanel api={apiFixture()} />);
    const dangerous = screen.queryAllByText(/push|release|tag|delete|destroy|kill/);
    expect(dangerous.length).toBe(0);
  });
});
