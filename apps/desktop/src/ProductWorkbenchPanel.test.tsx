import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProductWorkbenchPanel } from './ProductWorkbenchPanel';

const snapshot = {
  summary_cn: '从一句话需求到补丁验证的只读工作台。',
  read_only: true,
  current_stage_id: 'user_intent',
  stages: [
    { stage_id: 'user_intent', label_cn: '用户意图', status: 'active', detail_cn: '等待用户输入目标。' },
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
    summary_cn: '所有写入必须由用户人工批准。',
  },
  patch_approval: {
    label_cn: '补丁批准检查',
    warning_cn: '这里不会自动批准。',
    checks: [
      { check_id: 'preview_required', label_cn: '必须先看补丁预览', required: true, status: 'ready' },
      { check_id: 'human_approval_required', label_cn: '必须由用户批准', required: true, status: 'blocked' },
    ],
  },
  test_feedback: {
    label_cn: '白名单测试回填',
    warning_cn: '不允许任意 shell。',
    arbitrary_shell_allowed: false,
    commands: [
      { test_id: 'backend_unit', label_cn: '后端单元测试', status: 'ready' },
      { test_id: 'quality_gate', label_cn: '质量门', status: 'ready' },
    ],
  },
  failure_recovery: {
    label_cn: '失败与恢复检查',
    warning_cn: '不自动 retry，不自动 resume。',
    auto_retry_allowed: false,
    auto_resume_allowed: false,
    checks: [
      { check_id: 'failure_classified', label_cn: '失败已分类', required: true, status: 'ready' },
      { check_id: 'manual_resume_required', label_cn: '恢复必须人工确认', required: true, status: 'blocked' },
    ],
  },
  next_actions: ['先确认目标和补丁预览。'],
  updated_at: '2026-07-08T00:00:00Z',
};

describe('ProductWorkbenchPanel', () => {
  it('renders loading state', () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => new Promise(() => {}) }}
      />
    );

    expect(screen.getByText('加载 Agent 工作台中...')).toBeInTheDocument();
  });

  it('renders Chinese workflow stages and safety boundary', async () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('Agent 工作台')).toBeInTheDocument();
    expect(screen.getByText('用户意图')).toBeInTheDocument();
    expect(screen.getByText('人工批准')).toBeInTheDocument();
    expect(screen.getByText('测试验证')).toBeInTheDocument();
    expect(screen.getByText('所有写入必须由用户人工批准。')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('renders patch approval checklist without approval controls', async () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('补丁批准检查')).toBeInTheDocument();
    expect(screen.getByText('必须先看补丁预览')).toBeInTheDocument();
    expect(screen.getByText('必须由用户批准')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /批准/ })).toBeNull();
  });

  it('renders test feedback whitelist without arbitrary command input', async () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('白名单测试回填')).toBeInTheDocument();
    expect(screen.getByText('后端单元测试')).toBeInTheDocument();
    expect(screen.getByText('质量门')).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('renders failure recovery checks without retry controls', async () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('失败与恢复检查')).toBeInTheDocument();
    expect(screen.getByText('失败已分类')).toBeInTheDocument();
    expect(screen.getByText('恢复必须人工确认')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /重试|恢复/ })).toBeNull();
  });

  it('renders lane summaries and next actions', async () => {
    render(
      <ProductWorkbenchPanel
        api={{ fetchProductWorkbench: () => Promise.resolve(snapshot) }}
      />
    );

    expect(await screen.findByText('补丁预览')).toBeInTheDocument();
    expect(screen.getByText('测试回填')).toBeInTheDocument();
    expect(screen.getByText('先确认目标和补丁预览。')).toBeInTheDocument();
  });
});
