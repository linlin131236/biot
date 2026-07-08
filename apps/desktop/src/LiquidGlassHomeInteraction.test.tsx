import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { LiquidGlassHome } from './LiquidGlassHome';
import type { LiquidGlassHomeProps } from './LiquidGlassTypes';

function createProps(overrides: Partial<LiquidGlassHomeProps> = {}): LiquidGlassHomeProps {
  return {
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
    workspacePath: 'D:/Bolt/Bolt',
    coreStatus: 'ok',
    runId: 'run_143',
    legacyPanels: <div>工程面板内容</div>,
    ...overrides,
  };
}

function renderHome(overrides: Partial<LiquidGlassHomeProps> = {}) {
  const props = createProps(overrides);
  render(<LiquidGlassHome {...props} />);
  return props;
}

describe('LiquidGlassHome interaction cockpit', () => {
  it('renders a live task cockpit with workspace, permission, run, and core status', () => {
    renderHome();

    const cockpit = screen.getByRole('region', { name: '任务驾驶舱' });

    expect(cockpit).toHaveClass('biotCockpitPanel', 'biotLiquidBorder');
    expect(within(cockpit).getByText('当前项目')).toBeInTheDocument();
    expect(within(cockpit).getByText('Bolt')).toBeInTheDocument();
    expect(within(cockpit).getByText('权限边界')).toBeInTheDocument();
    expect(within(cockpit).getByText('写入需人工批准')).toBeInTheDocument();
    expect(within(cockpit).getByText('运行状态')).toBeInTheDocument();
    expect(within(cockpit).getByText('正在运行')).toBeInTheDocument();
    expect(within(cockpit).getByText('核心服务')).toBeInTheDocument();
    expect(within(cockpit).getByText('在线')).toBeInTheDocument();
  });

  it('routes recommended task cards to existing safe actions', () => {
    const props = renderHome();
    const recommendedTasks = screen.getByRole('region', { name: '推荐任务' });

    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：读取文件并解释代码' }));
    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：查看待批准权限' }));
    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：运行白名单测试' }));
    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：同步项目记忆' }));
    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：整理项目文档' }));
    fireEvent.click(within(recommendedTasks).getByRole('button', { name: '开始：查看执行时间线' }));

    expect(props.refreshTrace).toHaveBeenCalledTimes(1);
    expect(props.refreshPermissions).toHaveBeenCalledTimes(1);
    expect(props.runReview).toHaveBeenCalledTimes(1);
    expect(props.refreshMemory).toHaveBeenCalledTimes(1);
    expect(props.runGardener).toHaveBeenCalledTimes(1);
    expect(props.fetchTimeline).toHaveBeenCalledTimes(1);
  });

  it('keeps workspace-bound task cards waiting when no workspace is selected', () => {
    const props = renderHome({
      hasWorkspace: false,
      workspacePath: '工作区未选择',
      runId: null,
    });

    const cockpit = screen.getByRole('region', { name: '任务驾驶舱' });
    const recommendedTasks = screen.getByRole('region', { name: '推荐任务' });
    const readButton = within(recommendedTasks).getByRole('button', { name: '开始：读取文件并解释代码' });

    expect(within(cockpit).getByText('等待工作区')).toBeInTheDocument();
    expect(readButton).toBeDisabled();

    fireEvent.click(readButton);
    expect(props.refreshTrace).not.toHaveBeenCalled();
  });

  it('keeps run-bound task cards disabled until a run exists', () => {
    const props = renderHome({ runId: null });
    const recommendedTasks = screen.getByRole('region', { name: '推荐任务' });

    const readButton = within(recommendedTasks).getByRole('button', { name: '开始：读取文件并解释代码' });
    const permissionButton = within(recommendedTasks).getByRole('button', { name: '开始：查看待批准权限' });
    const memoryButton = within(recommendedTasks).getByRole('button', { name: '开始：同步项目记忆' });
    const gardenerButton = within(recommendedTasks).getByRole('button', { name: '开始：整理项目文档' });
    const timelineButton = within(recommendedTasks).getByRole('button', { name: '开始：查看执行时间线' });

    expect(readButton).toBeDisabled();
    expect(gardenerButton).toBeDisabled();
    expect(timelineButton).toBeDisabled();
    expect(permissionButton).toBeEnabled();
    expect(memoryButton).toBeEnabled();

    fireEvent.click(readButton);
    fireEvent.click(gardenerButton);
    fireEvent.click(timelineButton);
    fireEvent.click(permissionButton);
    fireEvent.click(memoryButton);

    expect(props.refreshTrace).not.toHaveBeenCalled();
    expect(props.runGardener).not.toHaveBeenCalled();
    expect(props.fetchTimeline).not.toHaveBeenCalled();
    expect(props.refreshPermissions).toHaveBeenCalledTimes(1);
    expect(props.refreshMemory).toHaveBeenCalledTimes(1);
  });

  it('does not render private address wording in the product UI', () => {
    renderHome();

    expect(document.body.textContent).not.toContain(String.fromCharCode(0x7238));
  });
});
