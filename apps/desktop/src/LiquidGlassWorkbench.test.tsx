import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiquidGlassWorkbench } from './LiquidGlassWorkbench';

const baseProps = {
  workspacePath: 'D:/Bolt/Bolt',
  coreStatus: 'ok',
  runId: 'run_141',
  goal: '',
  setGoal: vi.fn(),
  hasWorkspace: true,
  startRun: vi.fn(),
  createGoal: vi.fn(),
  runStep: vi.fn(),
  refreshTrace: vi.fn(),
  refreshMemory: vi.fn(),
  refreshPermissions: vi.fn(),
  runGardener: vi.fn(),
  fetchTimeline: vi.fn(),
  runReview: vi.fn(),
  changeWorkspace: vi.fn(),
  loadRecentSessions: vi.fn().mockResolvedValue([]),
  theme: 'dark' as const,
  setTheme: vi.fn(),
  onSaveTheme: vi.fn(),
  settings: { theme: 'dark', language: 'zh-CN', default_workspace: '', has_api_key: false },
  runtimeStatuses: [{
    runtime_id: 'hermes', implementation_version: null, protocol_type: 'acp', protocol_version: 'v1',
    capabilities: { messages: false, planning: false, tools: false, file_changes: false, shell: false, permissions: false, cancellation: false, resumption: false, mcp: false, images: false },
    state: 'release_unavailable', start_available: false, blocked_reason: 'release_unavailable', active_session_count: 0,
  }],
  refreshRuntimeStatuses: vi.fn(),
  fetcher: fetch,
  legacyPanels: <div>工程面板内容</div>,
};

describe('LiquidGlassWorkbench', () => {
  it('renders the liquid glass agent home in clean Chinese', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    expect(screen.getByText('Biot')).toBeInTheDocument();
    expect(screen.getByText('今天让 Biot 做什么？')).toBeInTheDocument();
    expect(screen.getByLabelText('任务目标')).toHaveAttribute('placeholder', '描述任务，或输入 / 选择能力');
    expect(screen.getByText('本地安全模式')).toBeInTheDocument();
    expect(screen.getByText('写入前永远等待人工批准')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\u7238\u7238/);
    expect(document.body.textContent).not.toMatch(/浠婂|鏂颁|娑叉|鐖哥|涓€|甯歌/);
  });

  it('keeps existing agent actions available from the home composer', () => {
    render(<LiquidGlassWorkbench {...baseProps} goal="读取 README 并总结" />);

    fireEvent.click(screen.getByRole('button', { name: '开始任务' }));
    fireEvent.click(screen.getByRole('button', { name: '创建目标' }));
    fireEvent.click(screen.getByRole('button', { name: '执行一步' }));

    expect(baseProps.startRun).toHaveBeenCalled();
    expect(baseProps.createGoal).toHaveBeenCalled();
    expect(baseProps.runStep).toHaveBeenCalled();
  });

  it('renders an honest unavailable Hermes Runtime state and supports refresh', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    expect(screen.getAllByText('等待受信任构建').length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: '刷新运行时状态' }));
    expect(baseProps.refreshRuntimeStatuses).toHaveBeenCalledOnce();
    expect(screen.queryByRole('button', { name: /启动 Hermes/ })).not.toBeInTheDocument();
  });

  it('shows the settings center with the approved categories', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));

    expect(screen.getByText('液态玻璃设置中心')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '常规' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '代码预览' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '模型设置' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'MCP 服务器' })).toBeInTheDocument();
    expect(screen.getByText('权限模式')).toBeInTheDocument();
  });

  it('returns from settings to the task workspace', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    expect(screen.getByRole('heading', { name: '液态玻璃设置中心' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '返回工作区' }));
    expect(screen.getByText('今天让 Biot 做什么？')).toBeInTheDocument();
  });

  it('shows read-only setting controls without fake action buttons', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '权限中心' }));

    const settingsStatus = screen.getByLabelText('当前设置状态');
    expect(screen.getByText('不可绕过')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '不可绕过' })).not.toBeInTheDocument();
    expect(within(settingsStatus).queryByRole('button', { name: '深色' })).not.toBeInTheDocument();
    expect(within(settingsStatus).queryByRole('button', { name: '简体中文' })).not.toBeInTheDocument();
  });

  it('marks unavailable composer affordances as disabled', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    expect(screen.getByRole('button', { name: /搜索/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: '已安排' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '添加上下文' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '语音输入' })).toBeDisabled();
  });

  it('renders section-specific product settings for code preview and model setup', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '代码预览' }));
    expect(screen.getByText('代码预览主题')).toBeInTheDocument();
    expect(screen.getByText('补丁差异、行号和长行折叠都在这里统一管理。')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '模型设置' }));
    expect(screen.getByText('模型提供方')).toBeInTheDocument();
    expect(screen.getByText('API 密钥只显示配置状态，不在界面回显明文。')).toBeInTheDocument();
  });

  it('renders a permission center surface without auto approval controls', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '权限中心' }));

    expect(screen.getByRole('heading', { name: '权限中心' })).toBeInTheDocument();
    expect(screen.getAllByText('待批准请求').length).toBeGreaterThan(0);
    expect(screen.getAllByText('写入门禁').length).toBeGreaterThan(0);
    expect(screen.getByText('所有写入、apply 和恢复动作都必须等待用户确认。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '自动批准' })).not.toBeInTheDocument();
  });

  it('renders a patch review surface with approval boundary copy', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '补丁审查' }));

    expect(screen.getByRole('heading', { name: '补丁审查' })).toBeInTheDocument();
    expect(screen.getAllByText('补丁预览').length).toBeGreaterThan(0);
    expect(screen.getAllByText('风险摘要').length).toBeGreaterThan(0);
    expect(screen.getAllByText('批准写入').length).toBeGreaterThan(0);
    expect(screen.getByText('只有用户确认后，补丁才允许进入写入流程。')).toBeInTheDocument();
  });

  it('renders an audit diagnostics surface with recovery guidance', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '审计诊断' }));

    expect(screen.getByRole('heading', { name: '审计诊断' })).toBeInTheDocument();
    expect(screen.getAllByText('审计时间线').length).toBeGreaterThan(0);
    expect(screen.getAllByText('诊断中心').length).toBeGreaterThan(0);
    expect(screen.getAllByText('恢复建议').length).toBeGreaterThan(0);
    expect(screen.getByText('阻断、警告、提示和下一步建议按优先级展示。')).toBeInTheDocument();
  });

  it('renders a validation release surface without publish controls', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '验证发布' }));

    expect(screen.getByRole('heading', { name: '验证发布' })).toBeInTheDocument();
    expect(screen.getAllByText('验证门禁').length).toBeGreaterThan(0);
    expect(screen.getAllByText('测试反馈').length).toBeGreaterThan(0);
    expect(screen.getAllByText('发布准备').length).toBeGreaterThan(0);
    expect(screen.getByText('这里只展示检查结果，不执行推送、发布或打标签。')).toBeInTheDocument();
  });

  it('renders an intelligence collaboration surface for memory team and queue', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getByRole('button', { name: '智能协作' }));

    expect(screen.getByRole('heading', { name: '智能协作' })).toBeInTheDocument();
    expect(screen.getAllByText('记忆索引').length).toBeGreaterThan(0);
    expect(screen.getAllByText('多 Agent 团队').length).toBeGreaterThan(0);
    expect(screen.getAllByText('多任务队列').length).toBeGreaterThan(0);
    expect(screen.getByText('统一展示记忆、角色分工和队列状态，不自动派发写入任务。')).toBeInTheDocument();
  });

  it('renders specific read-only surfaces for every remaining settings category', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));

    const categories = [
      ['技能', '技能管理'],
      ['子智能体', '子智能体'],
      ['MCP 服务器', 'MCP 服务器'],
      ['插件管理', '插件管理'],
      ['命令', '命令管理'],
      ['索引库', '索引库'],
      ['使用统计', '使用统计'],
      ['引导', '引导中心'],
    ];

    for (const [buttonName, headingName] of categories) {
      fireEvent.click(screen.getByRole('button', { name: buttonName }));
      expect(screen.getByRole('heading', { name: headingName })).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: '常规设置' })).not.toBeInTheDocument();
    }
  });

  it('can switch between dark and light liquid glass themes', () => {
    const setTheme = vi.fn();
    const { container, rerender } = render(<LiquidGlassWorkbench {...baseProps} theme="dark" setTheme={setTheme} onSaveTheme={vi.fn()} />);

    expect(container.querySelector('.biotLiquidShell')).toHaveAttribute('data-theme', 'dark');
    fireEvent.click(screen.getByRole('button', { name: '浅色' }));
    expect(setTheme).toHaveBeenCalledWith('light');
    // Simulate parent re-rendering with updated theme
    rerender(<LiquidGlassWorkbench {...baseProps} theme="light" setTheme={setTheme} onSaveTheme={vi.fn()} />);
    expect(container.querySelector('.biotLiquidShell')).toHaveAttribute('data-theme', 'light');
  });

  it('saves the settings-page theme through the parent callback', async () => {
    const onSaveTheme = vi.fn().mockResolvedValue(undefined);
    render(<LiquidGlassWorkbench {...baseProps} onSaveTheme={onSaveTheme} />);

    fireEvent.click(screen.getByRole('button', { name: '设置' }));
    fireEvent.click(screen.getAllByRole('button', { name: '浅色' }).at(-1)!);

    await waitFor(() => expect(onSaveTheme).toHaveBeenCalledWith('light'));
  });
});
