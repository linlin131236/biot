import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SessionRecoveryPanel } from './SessionRecoveryPanel';

const empty = { paused_tasks: [], total_paused: 0, recovery_policy: { total: 10, disclaimer: '策略就绪' } };
const full = { paused_tasks: [{ objective: '暂停任务', goal_id: 'g1' }], total_paused: 1, recovery_policy: { total: 10 } };

describe('SessionRecoveryPanel', () => {
  it('shows empty state', async () => {
    render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(empty) }} />);
    await waitFor(() => expect(screen.getByText(/暂无暂停/)).toBeTruthy());
  });

  it('shows paused tasks', async () => {
    render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(full) }} />);
    await waitFor(() => expect(screen.getByText('暂停任务')).toBeTruthy());
  });

  it('shows structured recovery policy', async () => {
    render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(full) }} />);
    await waitFor(() => expect(screen.getByText(/已加载 10 条恢复策略/)).toBeTruthy());
  });

  it('is read only', async () => {
    render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(empty) }} />);
    await waitFor(() => expect(screen.getByText(/只读会话恢复视图/)).toBeTruthy());
  });
});
