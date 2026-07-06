import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SideChatPanel } from './SideChatPanel';
import type { SteeringResult } from '@bolt/shared/autonomy';

describe('SideChatPanel', () => {
  const mockApi = {
    steerRun: vi.fn<() => Promise<SteeringResult>>(),
  };

  it('disables send when no runId', () => {
    render(<SideChatPanel runId={null} api={mockApi} />);
    const btn = screen.getByRole('button', { name: '发送指令' });
    expect(btn).toBeDisabled();
    expect(screen.getByText('暂无运行，无法发送')).toBeInTheDocument();
  });

  it('disables send when input is empty', () => {
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    const btn = screen.getByRole('button', { name: '发送指令' });
    expect(btn).toBeDisabled();
  });

  it('enables send when runId and non-empty input', () => {
    render(<SideChatPanel runId="run_1" api={mockApi} />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: '请先修测试' } });
    const btn = screen.getByRole('button', { name: '发送指令' });
    expect(btn).toBeEnabled();
  });

  it('calls steerRun and shows success message', async () => {
    mockApi.steerRun.mockResolvedValue({ status: 'injected' });
    render(<SideChatPanel runId="run_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: '请优先修复测试' } });
    const btn = screen.getByRole('button', { name: '发送指令' });
    fireEvent.click(btn);
    await waitFor(() => expect(screen.getByText('已加入当前任务')).toBeInTheDocument());
    expect(mockApi.steerRun).toHaveBeenCalledWith('http://core', 'run_1', '请优先修复测试');
  });

  it('shows failure message on error', async () => {
    mockApi.steerRun.mockRejectedValue(new Error('fail'));
    render(<SideChatPanel runId="run_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: '发送指令' }));
    await waitFor(() => expect(screen.getByText('发送失败')).toBeInTheDocument());
  });

  it('clears input after successful send', async () => {
    mockApi.steerRun.mockResolvedValue({ status: 'injected' });
    render(<SideChatPanel runId="run_1" api={mockApi} baseUrl="http://core" />);
    const input = screen.getByLabelText('侧聊内容');
    fireEvent.change(input, { target: { value: '指令' } });
    fireEvent.click(screen.getByRole('button', { name: '发送指令' }));
    await waitFor(() => expect(screen.getByText('已加入当前任务')).toBeInTheDocument());
    expect(input).toHaveValue('');
  });

  it('rendered HTML contains no dangerous globals', () => {
    const { container } = render(<SideChatPanel runId="run_1" api={mockApi} />);
    const html = container.innerHTML;
    expect(html).not.toMatch(/ipcRenderer|child_process|require\(['"]fs|shell\.|process\./);
  });
});
