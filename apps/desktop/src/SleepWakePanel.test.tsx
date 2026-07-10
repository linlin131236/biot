import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SleepWakePanel } from './SleepWakePanel';

const apiFixture = () => ({
  sleep: vi.fn().mockResolvedValue({ status: 'ok', state: 'sleeping', is_sleeping: true }),
  wake: vi.fn().mockResolvedValue({ status: 'ok', state: 'awake', is_sleeping: false }),
  fetchStatus: vi.fn().mockResolvedValue({ state: 'awake', is_sleeping: false }),
});

describe('SleepWakePanel', () => {
  it('renders title', () => {
    render(<SleepWakePanel api={apiFixture()} />);
    expect(screen.getByText('待机控制')).toBeInTheDocument();
  });

  it('shows awake status initially', async () => {
    render(<SleepWakePanel api={apiFixture()} />);
    expect(await screen.findByText(/awake/)).toBeInTheDocument();
  });

  it('sleeps and shows sleeping state', async () => {
    const api = apiFixture();
    render(<SleepWakePanel api={api} />);
    await screen.findByText(/awake/);
    fireEvent.click(screen.getByRole('button', { name: '进入待机' }));
    await waitFor(() => expect(api.sleep).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：sleeping')).toBeInTheDocument();
  });

  it('wakes and shows awake state', async () => {
    const api = apiFixture();
    render(<SleepWakePanel api={api} />);
    await screen.findByText(/awake/);
    fireEvent.click(screen.getByRole('button', { name: '进入待机' }));
    await waitFor(() => expect(api.sleep).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：sleeping')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '唤醒' }));
    await waitFor(() => expect(api.wake).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：awake')).toBeInTheDocument();
  });

  it('shows history', async () => {
    const api = apiFixture();
    render(<SleepWakePanel api={api} />);
    await screen.findByText(/awake/);
    fireEvent.click(screen.getByRole('button', { name: '进入待机' }));
    await waitFor(() => expect(api.sleep).toHaveBeenCalled());
    expect(await screen.findByText('当前状态：sleeping')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '唤醒' }));
    await waitFor(() => expect(api.wake).toHaveBeenCalled());
    expect(await screen.findByText(/最近操作/)).toBeInTheDocument();
  });

  it('has no dangerous buttons', () => {
    render(<SleepWakePanel api={apiFixture()} />);
    const dangerous = ['push', 'release', 'tag', 'delete', 'destroy', 'kill'];
    dangerous.forEach((text) => {
      expect(screen.queryByRole('button', { name: new RegExp(text, 'i') })).toBeNull();
    });
  });
});
