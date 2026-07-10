/**
 * ToolVerificationPanel tests (M166).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ToolVerificationPanel } from './ToolVerificationPanel';

function apiFixture(toolsData: Array<Record<string, unknown>> = []) {
  return {
    verifyTools: vi.fn().mockResolvedValue({ tools: toolsData }),
  };
}

describe('ToolVerificationPanel', () => {
  it('renders title', () => {
    render(<ToolVerificationPanel api={apiFixture()} />);
    expect(screen.getByText('工具验证')).toBeTruthy();
  });

  it('verifies tools and shows results', async () => {
    const api = apiFixture([
      { tool_name: 'git', status: 'ok', message: '可用' },
      { tool_name: 'node', status: 'error', message: '未安装' },
    ]);
    const fetcher = vi.fn();
    render(<ToolVerificationPanel fetcher={fetcher} api={api} />);
    fireEvent.click(screen.getByRole('button', { name: '验证工具链' }));
    await waitFor(() => expect(api.verifyTools).toHaveBeenCalledWith(fetcher));
    expect(await screen.findByText('git')).toBeTruthy();
    expect(screen.getByText('消息：可用')).toBeTruthy();
    expect(screen.getByText('消息：未安装')).toBeTruthy();
    expect(screen.getAllByText('状态：').length).toBeGreaterThanOrEqual(2);
  });

  it('shows empty results message when no tools returned', async () => {
    const api = apiFixture([]);
    render(<ToolVerificationPanel api={api} />);
    fireEvent.click(screen.getByText('验证工具链'));
    expect(await screen.findByText('未返回任何工具结果。')).toBeTruthy();
  });

  it('shows error on failure', async () => {
    const api = apiFixture();
    api.verifyTools.mockRejectedValueOnce(new Error('网络错误'));
    render(<ToolVerificationPanel api={api} />);
    fireEvent.click(screen.getByText('验证工具链'));
    expect(await screen.findByText('验证失败：网络错误')).toBeTruthy();
  });

  it('has no dangerous buttons', async () => {
    render(<ToolVerificationPanel api={apiFixture()} />);
    const dangerous = screen.queryAllByText(/push|release|tag|delete|destroy|kill/);
    expect(dangerous.length).toBe(0);
  });
});
