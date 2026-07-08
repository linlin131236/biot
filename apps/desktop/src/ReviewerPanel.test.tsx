/**
 * ReviewerPanel tests (M161).
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ReviewerPanel } from './ReviewerPanel';

function fakeApi(reviewData: Record<string, unknown> = {
  findings: [],
  evidence: [],
  tests_status: 'passed',
  residual_risks: [],
  verdict: 'approved',
  source_refs: [],
}) {
  return {
    reviewOutput: vi.fn().mockResolvedValue(reviewData),
    fetchVerdictLabel: vi.fn().mockResolvedValue({ verdict: 'approved', label: '已批准' }),
  };
}

describe('ReviewerPanel', () => {
  it('renders title', () => {
    render(<ReviewerPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('审查引擎')).toBeTruthy();
    expect(screen.getByText('独立审查，严格 Gate。P0/P1 阻止批准，P2 触发需修改。')).toBeTruthy();
  });

  it('reviews code with P0 finding and shows blocked verdict', async () => {
    const api = fakeApi({
      findings: [{ severity: 'P0', category: '安全', description: '注入漏洞', location: 'src/a.ts', suggestion: '修复注入' }],
      evidence: [],
      tests_status: 'failed',
      residual_risks: [],
      verdict: 'blocked',
      source_refs: [],
    });
    render(<ReviewerPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入代码变更内容'), { target: { value: 'code' } });
    fireEvent.click(screen.getByText('执行审查'));
    await waitFor(() => expect(screen.getByText('审查结果')).toBeTruthy());
    expect(screen.getByText('已阻塞')).toBeTruthy();
    expect(screen.getByText('注入漏洞')).toBeTruthy();
    expect(screen.getByText('安全')).toBeTruthy();
  });

  it('reviews code with P2 finding and shows changes_requested', async () => {
    const api = fakeApi({
      findings: [{ severity: 'P2', category: '样式', description: '缩进问题', location: 'src/b.ts', suggestion: '修复缩进' }],
      evidence: [],
      tests_status: 'passed',
      residual_risks: [],
      verdict: 'changes_requested',
      source_refs: [],
    });
    render(<ReviewerPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入代码变更内容'), { target: { value: 'code' } });
    fireEvent.click(screen.getByText('执行审查'));
    await waitFor(() => expect(screen.getByText('审查结果')).toBeTruthy());
    expect(screen.getByText('需修改')).toBeTruthy();
    expect(screen.getByText('缩进问题')).toBeTruthy();
  });

  it('reviews clean code and shows approved', async () => {
    const api = fakeApi({
      findings: [],
      evidence: [],
      tests_status: 'passed',
      residual_risks: [],
      verdict: 'approved',
      source_refs: [],
    });
    render(<ReviewerPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入代码变更内容'), { target: { value: 'clean code' } });
    fireEvent.click(screen.getByText('执行审查'));
    await waitFor(() => expect(screen.getByText('审查结果')).toBeTruthy());
    expect(screen.getByText('已批准')).toBeTruthy();
  });

  it('shows findings list with severity/category', async () => {
    const api = fakeApi({
      findings: [
        { severity: 'P1', category: '性能', description: '慢查询', location: 'src/db.ts', suggestion: '加索引' },
      ],
      evidence: ['log1'],
      tests_status: 'passed',
      residual_risks: ['R1'],
      verdict: 'changes_requested',
      source_refs: ['src/db.ts'],
    });
    render(<ReviewerPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入代码变更内容'), { target: { value: 'code' } });
    fireEvent.click(screen.getByText('执行审查'));
    await waitFor(() => expect(screen.getByText('审查发现')).toBeTruthy());
    expect(screen.getByText('P1')).toBeTruthy();
    expect(screen.getByText('性能')).toBeTruthy();
    expect(screen.getByText('慢查询')).toBeTruthy();
    expect(screen.getByText('位置：src/db.ts')).toBeTruthy();
    expect(screen.getByText('建议：加索引')).toBeTruthy();
    expect(screen.getByText('log1')).toBeTruthy();
    expect(screen.getByText('R1')).toBeTruthy();
    expect(screen.getByText('src/db.ts')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<ReviewerPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('执行审查')).toBeTruthy();
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });
});
