/** Tests for MemorySearchPanel — rendering, search, filter, safety. */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemorySearchPanel } from './MemorySearchPanel';

function makeApi(overrides: Partial<ReturnType<typeof makeMockApi>> = {}) {
  return {
    fetchDecisions: vi.fn().mockResolvedValue([]),
    fetchFailures: vi.fn().mockResolvedValue([]),
    fetchPreferences: vi.fn().mockResolvedValue([]),
    fetchProfile: vi.fn().mockResolvedValue({}),
    fetchCodeMap: vi.fn().mockResolvedValue([]),
    ...overrides,
  };
}
type MockApi = ReturnType<typeof makeApi>;

describe('MemorySearchPanel', () => {
  it('renders search input', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    expect(screen.getByPlaceholderText('输入关键词搜索记忆...')).toBeTruthy();
  });

  it('renders all category tabs', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    expect(screen.getByText('全部')).toBeTruthy();
    expect(screen.getByText('决策')).toBeTruthy();
    expect(screen.getByText('失败')).toBeTruthy();
    expect(screen.getByText('偏好')).toBeTruthy();
    expect(screen.getByText('项目')).toBeTruthy();
    expect(screen.getByText('代码地图')).toBeTruthy();
  });

  it('renders search button disabled when empty', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    const btn = screen.getByText('搜索');
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables search button with keyword', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    const input = screen.getByPlaceholderText('输入关键词搜索记忆...');
    fireEvent.change(input, { target: { value: '安全' } });
    const btn = screen.getByText('搜索');
    expect((btn as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows empty message after search with no results', async () => {
    render(<MemorySearchPanel api={makeApi()} />);
    const input = screen.getByPlaceholderText('输入关键词搜索记忆...');
    fireEvent.change(input, { target: { value: 'xyz' } });
    fireEvent.click(screen.getByText('搜索'));
    await waitFor(() => {
      expect(screen.getByText('未找到匹配的记忆记录，试试其他关键词。')).toBeTruthy();
    });
  });

  it('displays decision results', async () => {
    const api = makeApi({
      fetchDecisions: vi.fn().mockResolvedValue([{
        decision_id: '072-test', title: '测试决策', summary_cn: '测试摘要',
        source_refs: ['docs/decisions/072.md'],
      }]),
    });
    render(<MemorySearchPanel api={api} />);
    const input = screen.getByPlaceholderText('输入关键词搜索记忆...');
    fireEvent.change(input, { target: { value: '测试' } });
    fireEvent.click(screen.getByText('搜索'));
    await waitFor(() => {
      expect(screen.getByText('测试决策')).toBeTruthy();
    });
  });

  it('displays failure results with severity', async () => {
    const api = makeApi({
      fetchFailures: vi.fn().mockResolvedValue([{
        failure_id: 'f1', symptom_cn: '测试失败症状', fix_summary_cn: '修复方案',
        severity: 'P1', source_refs: ['docs/phase-57.md'],
      }]),
    });
    render(<MemorySearchPanel api={api} />);
    const input = screen.getByPlaceholderText('输入关键词搜索记忆...');
    fireEvent.change(input, { target: { value: '失败' } });
    fireEvent.click(screen.getByText('搜索'));
    await waitFor(() => {
      expect(screen.getByText('测试失败症状')).toBeTruthy();
      expect(screen.getByText('严重度: P1')).toBeTruthy();
    });
  });

  it('filters by tab', async () => {
    const api = makeApi({
      fetchDecisions: vi.fn().mockResolvedValue([{
        decision_id: 'd1', title: '决策标题', summary_cn: '摘要',
        source_refs: ['ref'],
      }]),
      fetchFailures: vi.fn().mockResolvedValue([{
        failure_id: 'f1', symptom_cn: '失败症状', fix_summary_cn: '修复',
        severity: 'P2', source_refs: ['ref'],
      }]),
    });
    render(<MemorySearchPanel api={api} />);
    // Click "失败" tab
    fireEvent.click(screen.getByText('失败'));
    const input = screen.getByPlaceholderText('输入关键词搜索记忆...');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.click(screen.getByText('搜索'));
    await waitFor(() => {
      // Only failures should show
      expect(screen.getByText('失败症状')).toBeTruthy();
    });
  });

  it('has read-only note', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    expect(screen.getByText(/只读搜索/)).toBeTruthy();
  });

  it('does not expose dangerous objects', () => {
    // The component must not access ipcRenderer, fs, shell, process
    const componentCode = MemorySearchPanel.toString();
    expect(componentCode).not.toContain('ipcRenderer');
    expect(componentCode).not.toContain('require("fs")');
    expect(componentCode).not.toContain('require("child_process")');
    expect(componentCode).not.toContain('process.');
  });

  it('has no write/delete/execute buttons', () => {
    render(<MemorySearchPanel api={makeApi()} />);
    // No save/write/delete/execute buttons
    expect(screen.queryByText('写入')).toBeNull();
    expect(screen.queryByText('删除')).toBeNull();
    expect(screen.queryByText('执行')).toBeNull();
    expect(screen.queryByText('保存')).toBeNull();
  });
});
