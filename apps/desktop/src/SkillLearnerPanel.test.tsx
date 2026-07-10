/**
 * SkillLearnerPanel tests (M162).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SkillLearnerPanel } from './SkillLearnerPanel';

function fakeApi(scanData: Record<string, unknown> = {
  keyword: '',
  patterns_found: 1,
  proposals_generated: 1,
  total_failures_tracked: 3,
  patterns: [{ pattern_id: 'p1', category: '网络', summary: '连接超时', failure_count: 2, suggestion: '增加重试' }],
  proposals: [{ proposal_id: 'pr1', title_cn: '添加重试机制', target_type: 'skill', status: 'draft', options: ['指数退避', '固定延迟'] }],
  message: '',
}) {
  return {
    autoScan: vi.fn().mockResolvedValue(scanData),
    recordFailure: vi.fn().mockResolvedValue({ recorded: true }),
  };
}

describe('SkillLearnerPanel', () => {
  it('renders title and subtitle', () => {
    render(<SkillLearnerPanel api={fakeApi()} />);
    expect(screen.getByText('技能学习器')).toBeTruthy();
    expect(screen.getByText('分析失败模式，提出改进建议。需用户审批后应用。')).toBeTruthy();
  });

  it('auto-scans and shows results', async () => {
    const api = fakeApi();
    const fetcher = vi.fn();
    render(<SkillLearnerPanel api={api} fetcher={fetcher} />);
    fireEvent.click(screen.getByText('自动扫描'));
    await waitFor(() => expect(screen.getByText('扫描结果')).toBeTruthy());
    expect(screen.getByText('模式发现')).toBeTruthy();
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('连接超时')).toBeTruthy();
    expect(screen.getByText('网络')).toBeTruthy();
    expect(screen.getByText('添加重试机制')).toBeTruthy();
    expect(screen.getByText('A. 指数退避')).toBeTruthy();
    expect(screen.getByText('B. 固定延迟')).toBeTruthy();
    expect(api.autoScan).toHaveBeenCalledWith('', fetcher);
  });

  it('sends keyword to auto-scan', async () => {
    const api = fakeApi();
    const fetcher = vi.fn();
    render(<SkillLearnerPanel api={api} fetcher={fetcher} />);
    fireEvent.change(screen.getByPlaceholderText('输入关键词筛选失败记忆'), { target: { value: 'timeout' } });
    fireEvent.click(screen.getByText('自动扫描'));
    await waitFor(() => expect(screen.getByText('扫描结果')).toBeTruthy());
    expect(api.autoScan).toHaveBeenCalledWith('timeout', fetcher);
  });

  it('records a failure manually', async () => {
    const api = fakeApi();
    render(<SkillLearnerPanel api={api} />);
    fireEvent.click(screen.getByText('手动记录失败'));
    await waitFor(() => expect(api.recordFailure).toHaveBeenCalledTimes(1));
  });

  it('shows error and retry on failure', async () => {
    const api = fakeApi();
    api.autoScan.mockRejectedValueOnce(new Error('服务不可用'));
    render(<SkillLearnerPanel api={api} />);
    fireEvent.click(screen.getByText('自动扫描'));
    await waitFor(() => expect(screen.getByText('自动扫描失败：服务不可用')).toBeTruthy());
    expect(screen.getByText('重试')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<SkillLearnerPanel api={fakeApi()} />);
    expect(screen.getByText('自动扫描')).toBeTruthy();
    expect(screen.getByText('手动记录失败')).toBeTruthy();
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });

  it('shows empty state when no patterns or proposals found', async () => {
    const api = fakeApi({ patterns_found: 0, proposals_generated: 0, patterns: [], proposals: [] });
    render(<SkillLearnerPanel api={api} />);
    fireEvent.click(screen.getByText('自动扫描'));
    await waitFor(() => expect(screen.getAllByText('0').length).toBe(3));
  });

  it('resets to form after viewing results', async () => {
    const api = fakeApi();
    render(<SkillLearnerPanel api={api} />);
    fireEvent.click(screen.getByText('自动扫描'));
    await waitFor(() => expect(screen.getByText('新建扫描')).toBeTruthy());
    fireEvent.click(screen.getByText('新建扫描'));
    expect(screen.getByText('技能学习器')).toBeTruthy();
    expect(screen.getByText('自动扫描')).toBeTruthy();
  });
});
