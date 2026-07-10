import { useMemo, useState, useEffect } from 'react';
import { Activity, Folder, History, Search, Settings, ShieldCheck, Sparkles } from 'lucide-react';
import { LiquidGlassHome } from './LiquidGlassHome';
import { LiquidGlassSettings } from './LiquidGlassSettings';
import type { LiquidGlassWorkbenchProps, ThemeMode, ViewMode } from './LiquidGlassTypes';
import './liquidGlassShell.css';
import './liquidGlassPrimitives.css';
import './liquidGlassHome.css';
import './liquidGlassHomeInteraction.css';
import './liquidGlassSettings.css';

type RecentSession = {
  id: string;
  title: string;
  time: string;
  status: string;
};

export function LiquidGlassWorkbench(props: LiquidGlassWorkbenchProps) {
  const [view, setView] = useState<ViewMode>('home');
  const [activeSetting, setActiveSetting] = useState('general');
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const safeWorkspace = props.workspacePath || '工作区未选择';

  useEffect(() => {
    if (!props.hasWorkspace || !props.fetcher) {
      setRecentSessions([]);
      return;
    }
    let active = true;
    setSessionsLoading(true);
    props.loadRecentSessions(20, props.fetcher).then((sessions) => {
      if (active) { setRecentSessions(sessions); setSessionsLoading(false); }
    }).catch(() => {
      if (active) { setRecentSessions([]); setSessionsLoading(false); }
    });
    return () => { active = false; };
  }, [props.hasWorkspace, props.loadRecentSessions, props.fetcher]);

  async function handleThemeChange(next: ThemeMode) {
    props.setTheme(next);
    props.onSaveTheme(next);
  }

  return (
    <main className="biotLiquidShell" data-theme={props.theme}>
      <aside className="biotRail">
        <div className="biotBrand">
          <div className="biotLogo">B</div>
          <div>
            <strong>Biot</strong>
            <span>本地 Agent 工作台</span>
          </div>
        </div>

        <nav className="biotNav" aria-label="主导航">
          <button type="button" className={view === 'home' ? 'active' : ''} onClick={() => setView('home')}>
            <Sparkles size={18} /> 新任务 <span>Ctrl+N</span>
          </button>
          <button type="button" disabled aria-disabled="true"><Search size={18} /> 搜索 <span>Ctrl+K</span></button>
          <button type="button" disabled aria-disabled="true"><History size={18} /> 已安排</button>
          <button type="button" className={view === 'settings' ? 'active' : ''} onClick={() => setView('settings')}>
            <Settings size={18} /> 设置
          </button>
        </nav>

        <div className="biotProjectBlock">
          <div className="biotBlockTitle">
            <span>项目</span>
            <button type="button" onClick={props.changeWorkspace} aria-label={props.hasWorkspace ? '切换项目' : '添加项目'}>+</button>
          </div>
          <button type="button" className="biotProjectButton" onClick={props.changeWorkspace}>
            <Folder size={18} /> {props.hasWorkspace ? '更换工作区' : '选择工作区'}
          </button>
          <div className="biotWorkspacePath">{safeWorkspace}</div>
        </div>

        <div className="biotRecent">
          <div className="biotBlockTitle"><span>最近会话</span><span>只读</span></div>
          {sessionsLoading ? (
            <p className="biotRecentEmpty">加载中...</p>
          ) : (recentSessions?.length ?? 0) === 0 ? (
            <p className="biotRecentEmpty">暂无最近会话</p>
          ) : (
            recentSessions.map((item) => (
              <div className="biotRecentItem" key={item.id}>
                <i data-status={item.status === 'completed' ? 'green' : item.status === 'failed' ? 'red' : 'amber'} />
                <span>{item.title}</span>
                <small>{item.time || '—'}</small>
              </div>
            ))
          )}
        </div>

        <div className="biotUserCard">
          <div className="biotAvatar">U</div>
          <div><strong>用户</strong><span><ShieldCheck size={14} /> 本地安全模式</span></div>
          <Activity size={18} />
        </div>
      </aside>

      <section className="biotMainSurface">
        <TopBar theme={props.theme} setTheme={props.setTheme} coreStatus={props.coreStatus} runId={props.runId} onThemeChange={handleThemeChange} />
        {view === 'home' ? (
          <LiquidGlassHome
            goal={props.goal}
            setGoal={props.setGoal}
            hasWorkspace={props.hasWorkspace}
            startRun={props.startRun}
            createGoal={props.createGoal}
            runStep={props.runStep}
            refreshTrace={props.refreshTrace}
            refreshMemory={props.refreshMemory}
            refreshPermissions={props.refreshPermissions}
            runGardener={props.runGardener}
            fetchTimeline={props.fetchTimeline}
            runReview={props.runReview}
            workspacePath={safeWorkspace}
            coreStatus={props.coreStatus}
            runId={props.runId}
            error={props.error}
            toolFlow={props.toolFlow}
            modelPanel={props.modelPanel}
            legacyPanels={props.legacyPanels}
          />
        ) : (
          <LiquidGlassSettings
            activeSetting={activeSetting}
            onBack={() => setView('home')}
            setActiveSetting={setActiveSetting}
            settings={props.settings}
            onSaveTheme={props.onSaveTheme}
          />
        )}
      </section>
    </main>
  );
}

function TopBar({
  theme,
  setTheme,
  coreStatus,
  runId,
  onThemeChange,
}: {
  theme: ThemeMode;
  setTheme: (value: ThemeMode) => void;
  coreStatus: string;
  runId: string | null;
  onThemeChange: (next: ThemeMode) => void;
}) {
  return (
    <header className="biotWindowBar">
      <div className="biotThemeSwitch" aria-label="主题切换">
        <button type="button" onClick={() => { setTheme('dark'); onThemeChange('dark'); }} className={theme === 'dark' ? 'active' : ''}>深色</button>
        <button type="button" onClick={() => { setTheme('light'); onThemeChange('light'); }} className={theme === 'light' ? 'active' : ''}>浅色</button>
      </div>
      <div className="biotStatusPills">
        <span><i /> 核心服务 <strong>{coreStatus === 'ok' ? '本地' : '离线'}</strong></span>
        <span><i /> 运行状态 <strong>{runId ? '已绑定' : '无运行'}</strong></span>
        <span><i /> 写入前永远等待人工批准</span>
      </div>
    </header>
  );
}
