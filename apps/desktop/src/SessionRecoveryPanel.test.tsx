import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { SessionRecoveryPanel } from './SessionRecoveryPanel';

const empty = { paused_tasks: [], total_paused: 0, recovery_policy: { summary_cn: '策略就绪' } };
const full = { paused_tasks: [{ objective: '暂停任务', goal_id: 'g1' }], total_paused: 1, recovery_policy: { summary_cn: '自动恢复' } };

describe('SessionRecoveryPanel', () => {
  it('empty', async () => { render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/暂无暂停/)).toBeTruthy()); });
  it('full', async () => { render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(full) }} />); await waitFor(() => expect(screen.getByText('暂停任务')).toBeTruthy()); });
  it('readonly', async () => { render(<SessionRecoveryPanel baseUrl="t" api={{ fetchSessionRecovery: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy()); });
});
