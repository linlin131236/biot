/**
 * TestRunnerPanel tests (M157).
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TestRunnerPanel } from './TestRunnerPanel';

function fakeApi(data: Record<string, unknown>, history: TestRunResult[] = []) {
  return {
    fetchAvailableTests: vi.fn().mockResolvedValue(data),
    runTest: vi.fn().mockResolvedValue({ result: { test_id: 'backend_unit', status: 'passed', exit_code: 0, summary: '10 passed', output_snippet: '[已脱敏]', evidence_hash: 'abc123' } }),
    fetchTestHistory: vi.fn().mockResolvedValue({ history }),
  };
}

const availableData = {
  available_tests: {
    backend_unit: { description: '后端单元测试', timeout_seconds: 180 },
    desktop_test: { description: '桌面端测试', timeout_seconds: 120 },
  },
};

describe('TestRunnerPanel', () => {
  it('renders loading state', () => {
    render(<TestRunnerPanel baseUrl="http://test" api={fakeApi(availableData)} />);
    expect(screen.getByText('安全测试运行器')).toBeTruthy();
  });

  it('renders test options after loading', async () => {
    render(<TestRunnerPanel baseUrl="http://test" api={fakeApi(availableData)} />);
    expect(await screen.findByText('后端单元测试')).toBeTruthy();
    expect(screen.getByText('桌面端测试')).toBeTruthy();
  });

  it('shows confirmation dialog after clicking run', async () => {
    render(<TestRunnerPanel baseUrl="http://test" api={fakeApi(availableData)} />);
    await screen.findByText('后端单元测试');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'backend_unit' } });
    fireEvent.click(screen.getByText('运行'));
    expect(screen.getByText('确认运行测试')).toBeTruthy();
    expect(screen.getByText(/180s/)).toBeTruthy();
  });

  it('runs test and shows passed result', async () => {
    const api = fakeApi(availableData);
    render(<TestRunnerPanel baseUrl="http://test" api={api} />);
    await screen.findByText('后端单元测试');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'backend_unit' } });
    fireEvent.click(screen.getByText('运行'));
    fireEvent.click(screen.getByText('确认运行'));
    await waitFor(() => expect(screen.getByText('通过')).toBeTruthy());
  });

  it('shows error state on failure', async () => {
    const api = fakeApi(availableData);
    api.runTest.mockRejectedValueOnce(new Error('网络错误'));
    render(<TestRunnerPanel baseUrl="http://test" api={api} />);
    await screen.findByText('后端单元测试');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'backend_unit' } });
    fireEvent.click(screen.getByText('运行'));
    fireEvent.click(screen.getByText('确认运行'));
    await waitFor(() => expect(screen.getByText(/运行失败/)).toBeTruthy());
  });

  it('shows whitelist disclaimer', async () => {
    render(<TestRunnerPanel baseUrl="http://test" api={fakeApi(availableData)} />);
    expect(await screen.findByText(/仅白名单命令可运行/)).toBeTruthy();
  });

  it('displays redacted output from backend', async () => {
    const api = fakeApi(availableData);
    api.runTest.mockResolvedValueOnce({
      result: {
        test_id: 'backend_unit', status: 'passed', exit_code: 0,
        summary: '10 passed', output_snippet: '[已脱敏]',
        evidence_hash: 'abc123',
      },
    });
    render(<TestRunnerPanel baseUrl="http://test" api={api} />);
    await screen.findByText('后端单元测试');
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'backend_unit' } });
    fireEvent.click(screen.getByText('运行'));
    fireEvent.click(screen.getByText('确认运行'));
    await waitFor(() => expect(screen.getByText('通过')).toBeTruthy());
    // Backend is responsible for redaction; verify redacted placeholder is shown
    expect(screen.getByText('[已脱敏]')).toBeTruthy();
  });

  it('has no dangerous operation buttons', async () => {
    render(<TestRunnerPanel baseUrl="http://test" api={fakeApi(availableData)} />);
    await screen.findByText('后端单元测试');
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });
});
