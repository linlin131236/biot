import { ArrowUp, CheckCircle2, Folder, Mic, ShieldCheck } from 'lucide-react';
import type { LiquidGlassHomeProps } from './LiquidGlassTypes';

export function LiquidGlassHome(props: LiquidGlassHomeProps) {
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
        <div className="biotComposerBar">
          <button type="button" className="biotIconButton" aria-label="添加上下文">+</button>
          <span className="biotChip"><Folder size={17} /> 当前项目</span>
          <span className="biotChip accent"><ShieldCheck size={17} /> 完全访问</span>
          <span className="biotSpacer" />
          <button type="button" onClick={props.createGoal} disabled={!props.hasWorkspace}>目标</button>
          <button type="button" onClick={props.startRun} disabled={!props.hasWorkspace}>开始</button>
          <button type="button" onClick={props.runStep} disabled={!props.hasWorkspace}>一步</button>
          <button type="button" className="biotRoundButton" aria-label="语音输入"><Mic size={18} /></button>
          <button type="button" className="biotSendButton" aria-label="发送任务" onClick={props.startRun} disabled={!props.hasWorkspace}>
            <ArrowUp size={22} />
          </button>
        </div>
      </section>

      {props.error}

      <section className="biotCompatStatus" aria-label="工程状态">
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

      <div className="biotSuggestionList">
        <button type="button" onClick={props.refreshTrace}>读取文件并解释关键代码</button>
        <button type="button" onClick={props.refreshPermissions}>生成补丁预览，等待人工批准</button>
        <button type="button" onClick={props.runReview}>运行白名单测试并汇总结论</button>
        <button type="button" onClick={props.refreshMemory}>同步项目记忆快照</button>
        <button type="button" onClick={props.runGardener}>整理项目文档</button>
        <button type="button" onClick={props.fetchTimeline}>查看执行时间线</button>
      </div>

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

function CommandButton({
  children,
  disabled,
  onClick,
}: {
  children: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return <button type="button" onClick={onClick} disabled={disabled}>{children}</button>;
}
