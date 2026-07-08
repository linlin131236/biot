/**
 * PermissionCenterPanel tests.
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PermissionCenterPanel } from './PermissionCenterPanel';

function fakeApi(data: Record<string, unknown>) {
  return {
    fetchPermissionCenter: vi.fn().mockResolvedValue(data),
    grantPermission: vi.fn().mockResolvedValue({ status: 'executed' }),
    denyPermission: vi.fn().mockResolvedValue({ status: 'rejected' }),
  };
}

function fakeApiRejects(msg: string) {
  return {
    fetchPermissionCenter: vi.fn().mockRejectedValue(new Error(msg)),
    grantPermission: vi.fn(),
    denyPermission: vi.fn(),
  };
}

const emptyData = {
  items: [],
  total_pending: 0,
  high_risk_count: 0,
  medium_risk_count: 0,
  low_risk_count: 0,
  updated_at: '2026-07-08T00:00:00Z',
};

const pendingData = {
  items: [
    {
      id: 'perm_p1',
      request_id: 'p1',
      run_id: 'r1',
      tool: 'shell_executor',
      tool_cn: '命令行执行',
      operation: 'execute',
      operation_cn: '执行',
      payload_summary: '{"cmd":"npm test"}',
      reason: '需要运行测试',
      status: 'pending_permission',
      status_cn: '等待批准',
      risk_level: 'high',
      risk_label_cn: '高风险',
      risk_explanation_cn: '此操作可能修改文件系统或执行系统命令。',
      impact_cn: '批准后将对项目文件或系统环境产生实际变更。',
      action_cn: '请确认内容后再批准。',
    },
    {
      id: 'perm_p2',
      request_id: 'p2',
      run_id: 'r1',
      tool: 'web_search',
      tool_cn: '网络搜索',
      operation: 'search',
      operation_cn: '搜索',
      payload_summary: '{"q":"test"}',
      reason: '需要搜索文档',
      status: 'pending_permission',
      status_cn: '等待批准',
      risk_level: 'low',
      risk_label_cn: '低风险',
      risk_explanation_cn: '此操作仅读取或查询信息。',
      impact_cn: '批准后仅执行信息查询操作。',
      action_cn: '请确认内容后再批准。',
    },
  ],
  total_pending: 2,
  high_risk_count: 1,
  medium_risk_count: 0,
  low_risk_count: 1,
  updated_at: '2026-07-08T00:00:00Z',
};

describe('PermissionCenterPanel', () => {
  it('renders loading state', () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(emptyData)} />);
    expect(screen.getByText('加载中...')).toBeTruthy();
  });

  it('renders empty state', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(emptyData)} />);
    await waitFor(() => {
      expect(screen.getByText(/没有待处理的权限请求/)).toBeTruthy();
    });
  });

  it('renders pending permissions', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(pendingData)} />);
    await waitFor(() => {
      expect(screen.getByText('命令行执行')).toBeTruthy();
      expect(screen.getByText('网络搜索')).toBeTruthy();
    });
  });

  it('shows high risk badge', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(pendingData)} />);
    await waitFor(() => {
      const badges = screen.getAllByText('高风险');
      expect(badges.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('shows risk explanation', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(pendingData)} />);
    await waitFor(() => {
      expect(screen.getByText(/修改文件系统/)).toBeTruthy();
    });
  });

  it('shows impact description', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(pendingData)} />);
    await waitFor(() => {
      expect(screen.getByText(/实际变更/)).toBeTruthy();
    });
  });

  it('shows error state', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApiRejects('网络错误')} />);
    await waitFor(() => {
      expect(screen.getByText(/加载失败/)).toBeTruthy();
    });
  });

  it('shows PermissionGate note', async () => {
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(emptyData)} />);
    await waitFor(() => {
      expect(screen.getByText(/所有批准和拒绝都会走 PermissionGate/)).toBeTruthy();
    });
  });

  it('approves permission only after user click and refreshes list', async () => {
    const api = fakeApi(pendingData);
    api.fetchPermissionCenter
      .mockResolvedValueOnce(pendingData)
      .mockResolvedValueOnce(emptyData);
    render(<PermissionCenterPanel baseUrl="http://test" api={api} />);
    await screen.findByText('命令行执行');

    fireEvent.click(screen.getAllByText('批准并执行')[0]);

    await waitFor(() => {
      expect(api.grantPermission).toHaveBeenCalledWith('http://test', 'p1');
      expect(api.fetchPermissionCenter).toHaveBeenCalledTimes(2);
    });
    expect(screen.getByText(/已批准并执行/)).toBeTruthy();
  });

  it('rejects permission only after user click and refreshes list', async () => {
    const api = fakeApi(pendingData);
    api.fetchPermissionCenter
      .mockResolvedValueOnce(pendingData)
      .mockResolvedValueOnce(emptyData);
    render(<PermissionCenterPanel baseUrl="http://test" api={api} />);
    await screen.findByText('命令行执行');

    fireEvent.click(screen.getAllByText('拒绝')[0]);

    await waitFor(() => {
      expect(api.denyPermission).toHaveBeenCalledWith('http://test', 'p1');
      expect(api.fetchPermissionCenter).toHaveBeenCalledTimes(2);
    });
    expect(screen.getByText(/已拒绝/)).toBeTruthy();
  });

  it('does not expose raw api key in payload_summary', async () => {
    const redactedData = {
      ...pendingData,
      items: [
        {
          ...pendingData.items[0],
          payload_summary: '{"api_key":"[已脱敏]"}',
        },
      ],
    };
    render(<PermissionCenterPanel baseUrl="http://test" api={fakeApi(redactedData)} />);
    await waitFor(() => {
      expect(screen.getByText('命令行执行')).toBeTruthy();
    });
    // The raw key must never appear in the rendered output
    expect(screen.queryByText(/sk-/)).toBeNull();
  });
});
