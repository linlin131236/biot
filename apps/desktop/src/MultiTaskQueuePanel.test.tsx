import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MultiTaskQueuePanel } from './MultiTaskQueuePanel';

const empty = { tasks: [], total: 0, closures_count: 0, goals_count: 0, graphs_count: 0 };
const full = { tasks: [{ type: 'goal', id: 'g1', title: '测试任务', status: 'running', risk: 'low' }], total: 1, closures_count: 0, goals_count: 1, graphs_count: 0 };

describe('MultiTaskQueuePanel', () => {
  it('empty', async () => { render(<MultiTaskQueuePanel api={{ fetchMultiTaskQueue: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/暂无匹配/)).toBeTruthy()); });
  it('full', async () => { render(<MultiTaskQueuePanel api={{ fetchMultiTaskQueue: vi.fn().mockResolvedValue(full) }} />); await waitFor(() => expect(screen.getByText('测试任务')).toBeTruthy()); });
  it('readonly', async () => { render(<MultiTaskQueuePanel api={{ fetchMultiTaskQueue: vi.fn().mockResolvedValue(empty) }} />); await waitFor(() => expect(screen.getByText(/只读/)).toBeTruthy()); });
});
