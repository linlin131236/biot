import {
  ArrowUp,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Folder,
  GitBranch,
  History,
  Layers3,
  Mic,
  Route,
  ShieldCheck,
  TestTube2,
} from 'lucide-react';
import type { LiquidGlassHomeProps } from './LiquidGlassTypes';
import { GlassButton, GlassPill, GlassToolbar } from './LiquidGlassPrimitives';

export function LiquidGlassHome(props: LiquidGlassHomeProps) {
  const coreOnline = props.coreStatus === 'ok';
  const runStatus = getRunStatus(props.hasWorkspace, coreOnline, props.runId);
  const projectName = props.hasWorkspace ? getProjectName(props.workspacePath) : '等待选择';
  const cockpitItems = [
    {
      label: '当前项目',
      value: projectName,
      tone: props.hasWorkspace ? 'success' : 'warning',
    },
    {
      label: '权限边界',
      value: '写入需人工批准',
      tone: 'warning',
    },
    {
      label: '运行状态',
      value: runStatus,
      tone: props.runId ? 'success' : props.hasWorkspace ? 'default' : 'warning',
    },
    {
      label: '核心服务',
      value: coreOnline ? '在线' : props.coreStatus,
      tone: coreOnline ? 'success' : 'danger',
    },
  ];
  const recommendedTasks = [
    {
      title: '读取文件并解释代码',
      description: '先看结构，再给出关键逻辑与风险点。',
      meta: '只读',
      icon: <FileText size={18} />,
      action: props.refreshTrace,
      disabled: !props.hasWorkspace || !props.runId,
    },
    {
      title: '查看待批准权限',
      description: '查看等待人工批准的工具请求。',
      meta: '权限',
      icon: <GitBranch size={18} />,
      action: props.refreshPermissions,
      disabled: !props.hasWorkspace,
    },
    {
      title: '评估验证门禁',
      description: '根据已回填的测试与构建结果评估审查门禁。',
      meta: '验证',
      icon: <TestTube2 size={18} />,
      action: props.runReview,
      disabled: !props.hasWorkspace,
    },
    {
      title: '同步项目记忆',
      description: '刷新决策、失败与偏好记忆快照。',
      meta: '记忆',
      icon: <Layers3 size={18} />,
      action: props.refreshMemory,
      disabled: !props.hasWorkspace,
    },
    {
      title: '整理项目文档',
      description: '归拢计划、复审门禁与状态记录。',
      meta: '文档',
      icon: <ClipboardCheck size={18} />,
      action: props.runGardener,
      disabled: !props.hasWorkspace || !props.runId,
    },
    {
      title: '查看执行时间线',
      description: '回看权限、工具、测试与审计链路。',
      meta: '审计',
      icon: <History size={18} />,
      action: props.fetchTimeline,
      disabled: !props.hasWorkspace || !props.runId,
    },
  ];

  return (
    <div className="biotHome">
      <div className="biotHeroMark">B</div>
      <div className="biotHero">
        <span>本地安全执行层</span>
        <h1>今天让 Biot 做什么？</h1>
        <p>本地权限受控，写入前永远等待人工批准。</p>
      </div>

      <section className="biotComposer biotLiquidBorder" aria-label="Agent 任务输入">
        <textarea
          aria-label="任务目标"
          placeholder="描述任务，或输入 / 选择能力"
          value={props.goal}
          onChange={(event) => props.setGoal(event.target.value)}
        />
        <GlassToolbar className="biotComposerBar" ariaLabel="任务操作">
          <GlassButton className="biotIconButton" aria-label="添加上下文" disabled>+</GlassButton>
          <GlassPill icon={<Folder size={17} />}>当前项目</GlassPill>
          <GlassPill tone="warning" icon={<ShieldCheck size={17} />}>完全访问</GlassPill>
          <span className="biotSpacer" />
          <GlassButton onClick={props.createGoal} disabled={!props.hasWorkspace}>目标</GlassButton>
          <GlassButton onClick={props.startRun} disabled={!props.hasWorkspace}>开始</GlassButton>
          <GlassButton onClick={props.runStep} disabled={!props.hasWorkspace}>一步</GlassButton>
          <GlassButton className="biotRoundButton" aria-label="语音输入" icon={<Mic size={18} />} disabled />
          <GlassButton variant="primary" className="biotSendButton" aria-label="发送任务" onClick={props.startRun} disabled={!props.hasWorkspace}>
            <ArrowUp size={22} />
          </GlassButton>
        </GlassToolbar>
      </section>

      {props.error}

      <section className="biotCockpitPanel biotLiquidBorder" aria-label="任务驾驶舱">
        <div className="biotCockpitHeader">
          <span><Route size={16} /> 任务驾驶舱</span>
          <strong>{props.runId ? '活跃运行' : '未绑定运行'}</strong>
        </div>
        <div className="biotCockpitGrid">
          {cockpitItems.map((item) => (
            <div className="biotCockpitItem" data-tone={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="biotCompatStatus biotCompatibilityStatus" aria-label="工程状态">
        <span>Agent Core 状态</span><strong>{props.coreStatus}</strong>
        <span>工作区</span><strong>{props.hasWorkspace ? '已选择' : '未选择'}</strong>
        <span>核心服务地址</span><strong>由 Agent Core 管理</strong>
        <span>当前运行</span><strong>{props.runId || '无'}</strong>
      </section>

      <section className="biotCommandStrip" aria-label="Agent 快捷操作">
        <CommandButton onClick={props.startRun} disabled={!props.hasWorkspace}>开始任务</CommandButton>
        <CommandButton onClick={props.createGoal} disabled={!props.hasWorkspace}>创建目标</CommandButton>
        <CommandButton onClick={props.runStep} disabled={!props.hasWorkspace}>执行一步</CommandButton>
        <CommandButton onClick={props.refreshTrace}>刷新轨迹</CommandButton>
        <CommandButton onClick={props.refreshMemory}>刷新记忆</CommandButton>
        <CommandButton onClick={props.refreshPermissions}>刷新权限</CommandButton>
        <CommandButton onClick={props.runGardener} disabled={!props.hasWorkspace}>整理文档</CommandButton>
        <CommandButton onClick={props.fetchTimeline} disabled={!props.hasWorkspace}>时间线</CommandButton>
        <CommandButton onClick={props.runReview}>审查</CommandButton>
      </section>

      <section className="biotTaskCards" aria-label="推荐任务">
        {recommendedTasks.map((task) => (
          <article className="biotTaskCard biotLiquidBorder" key={task.title}>
            <div className="biotTaskIcon">{task.icon}</div>
            <div className="biotTaskBody">
              <div className="biotTaskHeader">
                <strong>{task.title}</strong>
                <span>{task.meta}</span>
              </div>
              <p>{task.description}</p>
            </div>
            <GlassButton
              aria-label={`开始：${task.title}`}
              onClick={task.action}
              disabled={task.disabled}
            >
              开始
            </GlassButton>
          </article>
        ))}
      </section>

      <div className="biotSafetyDock">
        <span><CheckCircle2 size={17} /> 本地</span>
        <span><ShieldCheck size={17} /> 权限安全</span>
        <span>未自动执行</span>
        <span>测试待运行</span>
      </div>

      <details className="biotLegacyPanels" open>
        <summary>工程面板</summary>
        {props.toolFlow}
        {props.modelPanel}
        <div className="panels">{props.legacyPanels}</div>
      </details>
    </div>
  );
}

function getRunStatus(hasWorkspace: boolean, coreOnline: boolean, runId: string | null) {
  if (!hasWorkspace) {
    return '等待工作区';
  }
  if (!coreOnline) {
    return '核心服务异常';
  }
  if (runId) {
    return '正在运行';
  }
  return '准备就绪';
}

function getProjectName(workspacePath: string) {
  const parts = workspacePath.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] || '已选择';
}

function CommandButton({
  children,
  disabled,
  onClick,
}: {
  children: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return <GlassButton onClick={onClick} disabled={disabled}>{children}</GlassButton>;
}
