import {
  Activity,
  Bot,
  Code2,
  Database,
  FileDiff,
  Gauge,
  Hammer,
  Plug,
  Rocket,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Terminal,
} from 'lucide-react';
import { GlassButton } from './LiquidGlassPrimitives';
import { LiquidGlassSettingsSurface } from './LiquidGlassSettingsSurfaces';

const settingItems = [
  { id: 'general', label: '常规', icon: SlidersHorizontal },
  { id: 'code', label: '代码预览', icon: Code2 },
  { id: 'model', label: '模型设置', icon: Database },
  { id: 'permission', label: '权限中心', icon: ShieldCheck },
  { id: 'patch', label: '补丁审查', icon: FileDiff },
  { id: 'audit', label: '审计诊断', icon: Activity },
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
          <GlassButton className="active">深色</GlassButton>
          <GlassButton>浅色</GlassButton>
          <GlassButton>简体中文</GlassButton>
        </div>
        <LiquidGlassSettingsSurface activeSetting={activeSetting} />
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
