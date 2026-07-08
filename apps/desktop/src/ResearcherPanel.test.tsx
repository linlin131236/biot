/**
 * ResearcherPanel tests (M159).
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ResearcherPanel } from './ResearcherPanel';

const scopesData = {
  scopes: [
    { value: 'project_docs', label: '项目文档' },
    { value: 'bincloud_refs', label: 'BinCloud 参考资料' },
    { value: 'code_map', label: '代码地图' },
    { value: 'decision_memory', label: '决策记忆' },
    { value: 'failure_memory', label: '失败记忆' },
  ],
};

function fakeApi(briefData: Record<string, unknown> = { brief_id: 'b1', title: 'title', question: 'question', scope: 'code_map', status: 'created' }, resultData: Record<string, unknown> = { brief_id: 'b1', summary_cn: 's', principles_cn: [], risks_cn: [], source_refs: [] }) {
  return {
    createBrief: vi.fn().mockResolvedValue(briefData),
    executeResearch: vi.fn().mockResolvedValue(resultData),
    fetchScopes: vi.fn().mockResolvedValue(scopesData),
  };
}

describe('ResearcherPanel', () => {
  it('renders title', () => {
    render(<ResearcherPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('研究员')).toBeTruthy();
    expect(screen.getByText('只读研究，不修改文件。')).toBeTruthy();
  });

  it('shows scope options', async () => {
    render(<ResearcherPanel baseUrl="http://test" api={fakeApi()} />);
    expect(await screen.findByText('项目文档')).toBeTruthy();
    expect(screen.getByText('BinCloud 参考资料')).toBeTruthy();
    expect(screen.getByText('代码地图')).toBeTruthy();
    expect(screen.getByText('决策记忆')).toBeTruthy();
    expect(screen.getByText('失败记忆')).toBeTruthy();
  });

  it('creates brief and shows it', async () => {
    const api = fakeApi();
    render(<ResearcherPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入研究标题'), { target: { value: 'title' } });
    fireEvent.change(screen.getByPlaceholderText('输入研究问题'), { target: { value: 'question' } });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'code_map' } });
    fireEvent.click(screen.getByText('创建摘要'));
    await waitFor(() => expect(screen.getByText('研究摘要')).toBeTruthy());
    expect(screen.getByText('title')).toBeTruthy();
  });

  it('executes research and shows results', async () => {
    const api = fakeApi();
    const resultData = { brief_id: 'b1', summary_cn: '研究摘要内容', principles_cn: ['原则1'], risks_cn: ['风险1'], source_refs: [{ title: '来源A', url: 'http://a' }] };
    api.executeResearch.mockResolvedValueOnce(resultData);
    render(<ResearcherPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入研究标题'), { target: { value: 'title' } });
    fireEvent.change(screen.getByPlaceholderText('输入研究问题'), { target: { value: 'question' } });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'code_map' } });
    fireEvent.click(screen.getByText('创建摘要'));
    await waitFor(() => expect(screen.getByText('执行研究')).toBeTruthy());
    fireEvent.click(screen.getByText('执行研究'));
    await waitFor(() => expect(screen.getByText('研究结果')).toBeTruthy());
    expect(screen.getByText('研究摘要内容')).toBeTruthy();
    expect(screen.getByText('原则1')).toBeTruthy();
    expect(screen.getByText('风险1')).toBeTruthy();
    expect(screen.getByText('来源A')).toBeTruthy();
  });

  it('shows error state', async () => {
    const api = fakeApi();
    api.createBrief.mockRejectedValueOnce(new Error('网络错误'));
    render(<ResearcherPanel baseUrl="http://test" api={api} />);
    fireEvent.change(screen.getByPlaceholderText('输入研究标题'), { target: { value: 'title' } });
    fireEvent.change(screen.getByPlaceholderText('输入研究问题'), { target: { value: 'question' } });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'code_map' } });
    fireEvent.click(screen.getByText('创建摘要'));
    await waitFor(() => expect(screen.getByText(/创建摘要失败/)).toBeTruthy());
  });

  it('has no dangerous buttons', async () => {
    render(<ResearcherPanel baseUrl="http://test" api={fakeApi()} />);
    expect(screen.getByText('创建摘要')).toBeTruthy();
    const dangerous = screen.queryAllByText(/push|release|tag|delete|rm -rf|format/);
    expect(dangerous.length).toBe(0);
  });
});
