import {
  Bot,
  Code2,
  Database,
  Gauge,
  Hammer,
  Plug,
  Rocket,
  Search,
  SlidersHorizontal,
  Sparkles,
  Terminal,
} from 'lucide-react';

const settingItems = [
  { id: 'general', label: '常规', icon: SlidersHorizontal },
  { id: 'code', label: '代码预览', icon: Code2 },
  { id: 'model', label: '模型设置', icon: Database },
  { id: 'skills', label: '技能', icon: Sparkles },
  { id: 'agents', label: '子智能体', icon: Bot },
  { id: 'mcp', label: 'MCP 服务器', icon: Plug },
  { id: 'plugins', label: '插件管理', icon: Hammer },
  { id: 'commands', label: '命令', icon: Terminal },
  { id: 'index', label: '索引库', icon: Search },
  { id: 'usage', label: '使用统计', icon: Gauge },
  { id: 'guide', label: '引导', icon: Rocket },
];

export function LiquidGlassSettings({
  activeSetting,
  setActiveSetting,
}: {
  activeSetting: string;
  setActiveSetting: (value: string) => void;
}) {
  return (
    <div className="biotSettings">
      <aside className="biotSettingsNav">
        <button type="button" className="biotBackButton">返回工作区</button>
        {settingItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              type="button"
              key={item.id}
              className={activeSetting === item.id ? 'active' : ''}
              onClick={() => setActiveSetting(item.id)}
            >
              <Icon size={18} /> {item.label}
            </button>
          );
        })}
      </aside>

      <section className="biotSettingsContent">
        <SettingsHeader />
        <div className="biotSettingsTabs">
          <button type="button" className="active">深色</button>
          <button type="button">浅色</button>
          <button type="button">简体中文</button>
        </div>
        <GeneralCard />
        <PermissionCard />
        <NetworkCard />
      </section>
    </div>
  );
}

function SettingsHeader() {
  return (
    <div className="biotSettingsHeader">
      <div>
        <h1>液态玻璃设置中心</h1>
        <p>管理 Biot 的界面、模型、技能、子智能体和本地安全边界。</p>
      </div>
      <div className="biotStatusPills">
        <span><i /> 设置已保存</span>
        <span><i /> 本地配置</span>
        <span><i /> 权限安全</span>
      </div>
    </div>
  );
}

function GeneralCard() {
  return (
    <section className="biotGlassCard biotLiquidBorder">
      <SettingRow title="界面主题" detail="切换应用界面使用的主题外观。" control="深色液态玻璃" />
      <SettingRow title="界面语言" detail="选择应用 UI 的显示语言。" control="简体中文" />
      <SettingRow title="启动时打开" detail="选择启动后默认进入的页面。" control="Agent 工作台" />
    </section>
  );
}

function PermissionCard() {
  return (
    <section className="biotGlassCard biotLiquidBorder">
      <SettingRow title="权限模式" detail="写入、apply、恢复前都需要用户确认。" control="完全访问，写入需批准" />
      <SettingToggle title="自动执行" detail="不自动执行危险命令。" enabled={false} />
      <SettingToggle title="人工批准" detail="写入前永远等待用户确认。" enabled />
    </section>
  );
}

function NetworkCard() {
  return (
    <section className="biotGlassCard biotLiquidBorder">
      <SettingInput title="HTTP 代理" placeholder="留空直连，例如 http://127.0.0.1:7890" />
      <SettingInput title="No Proxy" placeholder="localhost,127.0.0.1" />
    </section>
  );
}

function SettingRow({ title, detail, control }: { title: string; detail: string; control: string }) {
  return (
    <div className="biotSettingRow">
      <div><strong>{title}</strong><span>{detail}</span></div>
      <button type="button">{control}</button>
    </div>
  );
}

function SettingToggle({ title, detail, enabled }: { title: string; detail: string; enabled: boolean }) {
  return (
    <div className="biotSettingRow">
      <div><strong>{title}</strong><span>{detail}</span></div>
      <button type="button" className={`biotSwitch ${enabled ? 'on' : ''}`} aria-label={title}><i /></button>
    </div>
  );
}

function SettingInput({ title, placeholder }: { title: string; placeholder: string }) {
  return (
    <label className="biotSettingInput">
      <span>{title}</span>
      <input placeholder={placeholder} />
      <button type="button">保存</button>
    </label>
  );
}
