import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SideChatPanel } from './SideChatPanel';
import type { SteeringResult } from '@bolt/shared/autonomy';

describe('SideChatPanel', () => {
  const okResult: SteeringResult = { status: 'injected' };
  const mockApi = { steerRun: vi.fn<() => Promise<SteeringResult>>() };

  it('renders heading 侧聊指令', () => {
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    expect(screen.getByText('侧聊指令')).toBeInTheDocument();
  });

  it('disables send when no runId', () => {
    render(<SideChatPanel runId={null} api={mockApi} />);
    expect(screen.getByRole('button', { name: '发送指令' })).toBeDisabled();
    expect(screen.getByText('暂无运行，无法发送')).toBeInTheDocument();
  });

  it('disables send when input is empty', () => {
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    expect(screen.getByRole('button', { name: '发送指令' })).toBeDisabled();
  });

  it('sends steering message and shows it in chat entries', async () => {
    mockApi.steerRun.mockResolvedValue(okResult);
    render(<SideChatPanel runId="run_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: '请先修测试' } });
    fireEvent.click(screen.getByRole('button', { name: '发送指令' }));
    await waitFor(() => expect(screen.getByText('请先修测试')).toBeInTheDocument());
    expect(mockApi.steerRun).toHaveBeenCalledWith('http://core', 'run_1', '请先修测试');
    // Input cleared after send
    expect(input).toHaveValue('');
  });

  it('shows error entry on send failure', async () => {
    mockApi.steerRun.mockRejectedValue(new Error('fail'));
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: 'bad' } });
    fireEvent.click(screen.getByRole('button', { name: '发送指令' }));
    await waitFor(() => expect(screen.getByText('发送失败')).toBeInTheDocument());
    // Entry still appears with error status
    expect(screen.getByText('bad').className).toContain('error');
  });

  it('sends on Enter key', async () => {
    mockApi.steerRun.mockResolvedValue(okResult);
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: '回车发送' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(screen.getByText('回车发送')).toBeInTheDocument());
  });

  it('rendered HTML has no dangerous globals', () => {
    const { container } = render(<SideChatPanel runId="run_1" api={mockApi} />);
    expect(container.innerHTML).not.toMatch(/ipcRenderer|child_process|require\(['"]fs|shell\.|process\./);
  });
});
