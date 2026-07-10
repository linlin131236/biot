/**
 * TaskHomePanel tests (M91).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TaskHomePanel } from './TaskHomePanel';

function fakeApi(data: Record<string, unknown>) {
  return {
    fetchTaskHome: vi.fn().mockResolvedValue(data),
  };
}

function fakeApiRejects(msg: string) {
  return {
    fetchTaskHome: vi.fn().mockRejectedValue(new Error(msg)),
  };
}

const emptyData = {
  current_goal: null,
  unfinished_goal_count: 0,
  pending_permission_count: 0,
  blocker_count: 0,
  warning_count: 0,
  active_task_count: 0,
  recent_events: [],
  next_suggestions: ['当前没有进行中的目标，可以创建一个新目标开始工作。'],
  updated_at: '2026-07-08T00:00:00Z',
};

const fullData = {
  current_goal: { id: 'g1', objective: '重构权限模块', status: 'running', step_count: 3, criteria: [], max_steps: 10, max_cost: 100, max_wall_time: 3600, workspace: '/tmp' },
  unfinished_goal_count: 2,
  pending_permission_count: 3,
  blocker_count: 1,
  warning_count: 2,
  active_task_count: 5,
  recent_events: [
    { code: 'D001', severity: 'blocking', severity_label: '阻断', summary: '审计文件损坏', suggestion: '运行修复脚本' },
    { code: 'D010', severity: 'warning', severity_label: '警告', summary: '权限队列积压', suggestion: '清理过期权限' },
  ],
  next_suggestions: [
    '当前有 1 个阻断项需要处理，请查看诊断中心了解详情。',
    '有 3 个权限请求等待批准，请前往权限中心处理。',
    '当前目标「重构权限模块」状态：运行中。',
  ],
  updated_at: '2026-07-08T00:00:00Z',
};

describe('TaskHomePanel', () => {
  it('renders loading state initially', () => {
    render(<TaskHomePanel api={fakeApi(emptyData)} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('renders empty state', async () => {
    render(<TaskHomePanel api={fakeApi(emptyData)} />);
    await waitFor(() => {
      expect(screen.getByText('暂无进行中的目标。')).toBeTruthy();
    });
  });

  it('renders full data', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      expect(screen.getByText('重构权限模块')).toBeTruthy();
      const statusElements = screen.getAllByText(/运行中/);
      expect(statusElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows blocker count when present', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      const matches = screen.getAllByText(/阻断/);
      expect(matches.length).toBeGreaterThan(0);
    });
  });

  it('shows pending permission count', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      expect(screen.getByText(/权限待批/)).toBeTruthy();
    });
  });

  it('shows suggestions', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      expect(screen.getByText(/权限请求等待批准/)).toBeTruthy();
    });
  });

  it('shows recent events', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      expect(screen.getByText(/审计文件损坏/)).toBeTruthy();
    });
  });

  it('shows error state', async () => {
    render(<TaskHomePanel api={fakeApiRejects('网络错误')} />);
    await waitFor(() => {
      expect(screen.getByText(/加载失败/)).toBeTruthy();
    });
  });

  it('has Chinese read-only note', async () => {
    render(<TaskHomePanel api={fakeApi(emptyData)} />);
    await waitFor(() => {
      expect(screen.getByText(/只读/)).toBeTruthy();
    });
  });

  it('has no approve/execute/delete buttons', async () => {
    render(<TaskHomePanel api={fakeApi(fullData)} />);
    await waitFor(() => {
      expect(screen.getByText('重构权限模块')).toBeTruthy();
    });
    // Verify no buttons with dangerous text exist
    const buttons = document.querySelectorAll('button');
    const buttonTexts = Array.from(buttons).map(b => b.textContent?.toLowerCase() || '');
    expect(buttonTexts.some(t => t.includes('push') || t.includes('delete') || t.includes('release') || t.includes('approve'))).toBe(false);
  });
});
