import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiquidGlassWorkbench } from './LiquidGlassWorkbench';

const baseProps = {
  workspacePath: 'D:/Bolt/Bolt',
  coreStatus: 'ok',
  runId: 'run_131',
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
  legacyPanels: <div>工程面板内容</div>,
};

describe('LiquidGlassWorkbench', () => {
  it('renders the liquid glass agent home in Chinese', () => {
    render(<LiquidGlassWorkbench {...baseProps} />);

    expect(screen.getByText('Biot')).toBeInTheDocument();
    expect(screen.getByText('今天让 Biot 做什么？')).toBeInTheDocument();
    expect(screen.getByLabelText('任务目标')).toHaveAttribute('placeholder', '描述任务，或输入 / 选择能力');
    expect(screen.getByText('本地安全模式')).toBeInTheDocument();
    expect(screen.getByText('写入前永远等待爸爸批准')).toBeInTheDocument();
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

  it('can switch between dark and light liquid glass themes', () => {
    const { container } = render(<LiquidGlassWorkbench {...baseProps} />);

    expect(container.querySelector('.biotLiquidShell')).toHaveAttribute('data-theme', 'dark');
    fireEvent.click(screen.getByRole('button', { name: '浅色' }));
    expect(container.querySelector('.biotLiquidShell')).toHaveAttribute('data-theme', 'light');
  });
});
