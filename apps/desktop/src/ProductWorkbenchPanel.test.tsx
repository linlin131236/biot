import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProductWorkbenchPanel } from './ProductWorkbenchPanel';

const snapshot = {
  summary_cn: '从一句话需求到补丁验证的只读工作台。',
  read_only: true,
  current_stage_id: 'user_intent',
  stages: [
    { stage_id: 'user_intent', label_cn: '用户意图', status: 'active', detail_cn: '等待爸爸输入目标。' },
    { stage_id: 'human_approval', label_cn: '人工批准', status: 'blocked', detail_cn: '写入前必须批准。' },
    { stage_id: 'run_tests', label_cn: '测试验证', status: 'ready', detail_cn: '只允许白名单测试。' },
  ],
  lanes: [
    { lane_id: 'patch', label_cn: '补丁预览', status: 'empty', detail_cn: '暂无补丁。' },
    { lane_id: 'test', label_cn: '测试回填', status: 'ready', detail_cn: '可查看测试结果。' },
  ],
  safety: {
    auto_apply_allowed: false,
    auto_approve_allowed: false,
    human_approval_required: true,
    dangerous_operations_blocked: true,
    summary_cn: '所有写入必须由爸爸人工批准。',
  },
  next_actions: ['先确认目标和补丁预览。'],
  updated_at: '2026-07-08T00:00:00Z',
};

describe('ProductWorkbenchPanel', () => {
  it('renders loading state', () => {
    render(
      <ProductWorkbenchPanel
        baseUrl="http://core"
        api={{ fetchProductWorkbench: () => new Promise(() => {}) }}
      />
    );

    expect(screen.getByText('加载 Agent 工作台中...')).toBeInTheDocument();
  });

  it('renders Chinese workflow stages and safety boundary', async () => {
    render(
      <ProductWorkbenchPanel
        baseUrl="http://core"
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('Agent 工作台')).toBeInTheDocument();
    expect(screen.getByText('用户意图')).toBeInTheDocument();
    expect(screen.getByText('人工批准')).toBeInTheDocument();
    expect(screen.getByText('测试验证')).toBeInTheDocument();
    expect(screen.getByText('所有写入必须由爸爸人工批准。')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('renders lane summaries and next actions', async () => {
    render(
      <ProductWorkbenchPanel
        baseUrl="http://core"
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('补丁预览')).toBeInTheDocument();
    expect(screen.getByText('测试回填')).toBeInTheDocument();
    expect(screen.getByText('先确认目标和补丁预览。')).toBeInTheDocument();
  });
});
