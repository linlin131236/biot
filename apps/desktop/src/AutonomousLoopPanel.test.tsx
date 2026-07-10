/**
 * AutonomousLoopPanel tests (M170).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutonomousLoopPanel } from './AutonomousLoopPanel';

function apiFixture(resultData: Record<string, unknown> = { status: 'completed', rounds_completed: 2, verdict: 'approved', trace: [] }) {
  return {
    runAutonomousLoop: vi.fn().mockResolvedValue(resultData),
  };
}

describe('AutonomousLoopPanel', () => {
  it('renders title', () => {
    render(<AutonomousLoopPanel api={apiFixture()} />);
    expect(screen.getByText('自主循环')).toBeTruthy();
  });

  it('runs autonomous loop and shows result', async () => {
    const api = apiFixture({ status: 'completed', rounds_completed: 3, verdict: 'approved', trace: [{ role: 'builder' }, { role: 'reviewer' }] });
    const fetcher = vi.fn();
    render(<AutonomousLoopPanel fetcher={fetcher} api={api} />);
    const numberInput = document.querySelector('input[type="number"]') as HTMLInputElement;
    fireEvent.change(numberInput, { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: '启动自主循环' }));
    await waitFor(() => expect(api.runAutonomousLoop).toHaveBeenCalledWith(expect.any(Object), fetcher));
    await waitFor(() => expect(screen.getByText('循环结果')).toBeTruthy());
    expect(screen.getAllByText(/completed/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/完成轮次：/)).toBeTruthy();
    expect(screen.getAllByText(/approved/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows trace entries', async () => {
    const api = apiFixture({ status: 'completed', rounds_completed: 1, verdict: 'approved', trace: [{ role: 'planner' }] });
    render(<AutonomousLoopPanel api={api} />);
    fireEvent.click(screen.getByText('启动自主循环'));
    await waitFor(() => expect(screen.getByText('执行轨迹')).toBeTruthy());
    expect(screen.getByText(/"role":"planner"/)).toBeTruthy();
  });

  it('shows error on failure', async () => {
    const api = apiFixture();
    api.runAutonomousLoop.mockRejectedValueOnce(new Error('循环失败'));
    render(<AutonomousLoopPanel api={api} />);
    fireEvent.click(screen.getByText('启动自主循环'));
    expect(await screen.findByText('启动自主循环失败：循环失败')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<AutonomousLoopPanel api={apiFixture()} />);
    const dangerous = screen.queryAllByText(/push|release|tag|delete|destroy|kill/);
    expect(dangerous.length).toBe(0);
  });
});
