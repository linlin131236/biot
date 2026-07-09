/**
 * AutoFixPanel tests (M167).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutoFixPanel } from './AutoFixPanel';

function apiFixture(resultData: Record<string, unknown> = { fixed: 2, remaining: 0, fixed_items: [], remaining_items: [] }) {
  return {
    autoFixReviewFindings: vi.fn().mockResolvedValue(resultData),
  };
}

describe('AutoFixPanel', () => {
  it('renders title', () => {
    render(<AutoFixPanel baseUrl="http://test" api={apiFixture()} />);
    expect(screen.getByRole('heading', { name: '自动修复' })).toBeTruthy();
  });

  it('auto-fixes and shows fixed/remaining counts', async () => {
    const api = apiFixture({ fixed: 3, remaining: 1, fixed_items: [{ id: 'f1' }], remaining_items: [{ id: 'r1' }], message: '修复完成' });
    const fetcher = vi.fn();
    render(<AutoFixPanel baseUrl="http://test" fetcher={fetcher} api={api} />);
    fireEvent.change(screen.getByPlaceholderText('[{"severity": "P0", "description": "示例问题"}]'), { target: { value: '[{"id":"1"}]' } });
    fireEvent.click(screen.getByRole('button', { name: '自动修复' }));
    await waitFor(() => expect(api.autoFixReviewFindings).toHaveBeenCalledWith('http://test', expect.any(Object), fetcher));
    await waitFor(() => expect(screen.getByText('修复结果')).toBeTruthy());
    expect(screen.getByText('3')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy();
    expect(screen.getByText('修复完成')).toBeTruthy();
  });

  it('shows error for invalid JSON', async () => {
    const api = apiFixture();
    render(<AutoFixPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('[{"severity": "P0", "description": "示例问题"}]'), { target: { value: '{invalid' } });
    fireEvent.click(screen.getByRole('button', { name: '自动修复' }));
    expect(await screen.findByText('findings JSON 格式无效，请检查输入。')).toBeTruthy();
  });

  it('shows error on API failure', async () => {
    const api = apiFixture();
    api.autoFixReviewFindings.mockRejectedValueOnce(new Error('修复失败'));
    render(<AutoFixPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('[{"severity": "P0", "description": "示例问题"}]'), { target: { value: '[]' } });
    fireEvent.click(screen.getByRole('button', { name: '自动修复' }));
    expect(await screen.findByText('自动修复失败：修复失败')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<AutoFixPanel baseUrl="http://test" api={apiFixture()} />);
    const dangerous = screen.queryAllByText(/push|release|tag|delete|destroy|kill/);
    expect(dangerous.length).toBe(0);
  });
});
