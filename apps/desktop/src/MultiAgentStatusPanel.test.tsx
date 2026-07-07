import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MultiAgentStatusPanel } from './MultiAgentStatusPanel';

const mockRoles = [
  { role_id: 'planner', name_cn: '规划者', task_count: 2, blocked_count: 0 },
  { role_id: 'builder', name_cn: '构建者', task_count: 3, blocked_count: 1 },
];
const mockBoard = { total_tasks: 5, by_role: { planner: 2, builder: 3 }, by_status: { pending: 3, in_progress: 2 }, blocked_tasks: [] };
const mockSubtasks = [
  { task_id: 't1', title_cn: '实现登录', assigned_role: 'builder', status: 'in_progress', status_label_cn: '进行中', risk_level: 'low', risk_label_cn: '低', source_refs: ['docs/spec.md'] },
  { task_id: 't2', title_cn: '代码审查', assigned_role: 'reviewer', status: 'pending', status_label_cn: '待办', risk_level: 'medium', risk_label_cn: '中', source_refs: [] },
];

const api = {
  fetchRoles: vi.fn().mockResolvedValue(mockRoles),
  fetchBoard: vi.fn().mockResolvedValue(mockBoard),
  fetchSubtasks: vi.fn().mockResolvedValue(mockSubtasks),
};

describe('MultiAgentStatusPanel', () => {
  it('renders component with title', async () => {
    render(<MultiAgentStatusPanel baseUrl="http://test" api={api} />);
    await waitFor(() => {
      expect(screen.getByText('多 Agent 状态')).toBeDefined();
    });
  });

  it('renders subtasks when loaded', async () => {
    render(<MultiAgentStatusPanel baseUrl="http://test" api={api} />);
    await waitFor(() => {
      expect(screen.getByText('实现登录')).toBeDefined();
      expect(screen.getByText('代码审查')).toBeDefined();
    });
  });

  it('shows source_refs', async () => {
    render(<MultiAgentStatusPanel baseUrl="http://test" api={api} />);
    await waitFor(() => {
      expect(screen.getByText(/docs\/spec\.md/)).toBeDefined();
    });
  });

  it('shows read-only note', async () => {
    render(<MultiAgentStatusPanel baseUrl="http://test" api={api} />);
    await waitFor(() => {
      expect(screen.getByText(/只读状态展示/)).toBeDefined();
    });
  });

  it('handles loading state', () => {
    const slowApi = { ...api, fetchRoles: vi.fn(() => new Promise(() => {})) };
    render(<MultiAgentStatusPanel baseUrl="http://test" api={slowApi} />);
    expect(screen.getByText('加载中…')).toBeDefined();
  });

  it('no dangerous objects exposed', async () => {
    render(<MultiAgentStatusPanel baseUrl="http://test" api={api} />);
    expect((globalThis as Record<string, unknown>).ipcRenderer).toBeUndefined();
  });
});
