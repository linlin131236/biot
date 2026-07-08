/**
 * TaskResultSummaryPanel tests (M158).
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TaskResultSummaryPanel } from './TaskResultSummaryPanel';
import type { TaskResultSummary } from '@bolt/shared/closure-summary';

const baseSummary: TaskResultSummary = {
  closure_id: 'cl_001',
  status: 'completed',
  steps: 3,
  duration_seconds: 125,
  changed_files: ['README.md', 'src/index.ts'],
  commands: ['pytest', 'build'],
  command_results: ['299 ok', 'build success'],
  final_output: null,
  error: null,
  review_summary: '审查通过',
  next_action: '建议：部署到生产环境',
  retry_count: 0,
  permission_requests: [],
};

describe('TaskResultSummaryPanel', () => {
  it('renders all fields when summary is provided', () => {
    render(<TaskResultSummaryPanel summary={baseSummary} loading={false} />);
    expect(screen.getByText('结果摘要')).toBeTruthy();
    expect(screen.getByText('completed')).toBeTruthy();
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('2分5秒')).toBeTruthy();
    expect(screen.getByText('README.md, src/index.ts')).toBeTruthy();
    expect(screen.getByText('299 ok')).toBeTruthy();
    expect(screen.getByText('审查通过')).toBeTruthy();
    expect(screen.getByText('建议：部署到生产环境')).toBeTruthy();
  });

  it('shows loading state', () => {
    render(<TaskResultSummaryPanel summary={null} loading={true} />);
    expect(screen.getByText('加载中…')).toBeTruthy();
  });

  it('returns null when summary is null and not loading', () => {
    const { container } = render(<TaskResultSummaryPanel summary={null} loading={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows error info when present', () => {
    const summary: TaskResultSummary = { ...baseSummary, error: '内存不足' };
    render(<TaskResultSummaryPanel summary={summary} loading={false} />);
    expect(screen.getByText('错误信息：')).toBeTruthy();
    expect(screen.getByText('内存不足')).toBeTruthy();
  });

  it('shows 无 when changed_files is empty', () => {
    const summary: TaskResultSummary = { ...baseSummary, changed_files: [] };
    render(<TaskResultSummaryPanel summary={summary} loading={false} />);
    expect(screen.getByText('无')).toBeTruthy();
  });
});
