import { GlassPanel, GlassPill } from './LiquidGlassPrimitives';

export type SettingMetric = {
  label: string;
  value: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

export type SettingRow = {
  title: string;
  detail: string;
  control: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

export type SettingSurface = {
  eyebrow: string;
  title: string;
  summary: string;
  metrics: SettingMetric[];
  rows: SettingRow[];
};

export type DesktopSettingsStatus = {
  theme: string;
  language: string;
  default_workspace: string;
  has_api_key: boolean;
  credential_revision?: number;
};

export type LiquidGlassSettingsProps = {
  activeSetting: string;
  onBack: () => void;
  setActiveSetting: (value: string) => void;
  settings: DesktopSettingsStatus | null;
  onSaveTheme: (theme: string) => Promise<void>;
};

export const settingItems = [
  { id: 'general', label: '常规' },
  { id: 'code', label: '代码预览' },
  { id: 'model', label: '模型设置' },
  { id: 'permission', label: '权限中心' },
  { id: 'patch', label: '补丁审查' },
  { id: 'audit', label: '审计诊断' },
  { id: 'validation', label: '验证发布' },
  { id: 'diagnostics', label: '诊断反馈' },
  { id: 'collaboration', label: '智能协作' },
  { id: 'skills', label: '技能' },
  { id: 'agents', label: '子智能体' },
  { id: 'mcp', label: 'MCP 服务器' },
  { id: 'plugins', label: '插件管理' },
  { id: 'commands', label: '命令' },
  { id: 'index', label: '索引库' },
  { id: 'usage', label: '使用统计' },
  { id: 'guide', label: '引导' },
];

export const surfaces: Record<string, SettingSurface> = {
  general: {
    eyebrow: '界面与启动',
    title: '常规设置',
    summary: '控制 Biot 的主题、语言、默认入口和本地安全提示。',
    metrics: [
      { label: '主题', value: '加载中...', tone: 'success' },
      { label: '语言', value: '加载中...' },
      { label: '启动页', value: 'Agent 工作台' },
    ],
    rows: [
      { title: '界面主题', detail: '深浅色液态玻璃主题保持同一套安全信息层级。', control: '加载中...', tone: 'success' },
      { title: '界面语言', detail: '所有用户可见文字使用中文，面向公开产品表达。', control: '加载中...' },
      { title: '启动时打开', detail: '启动后默认进入任务驾驶舱，设置中心保留在侧边导航。', control: 'Agent 工作台' },
      { title: '本地 Agent Core', detail: '由 Bolt 桌面端自动管理，用户不可配置地址。', control: '本地 Agent Core · 由 Bolt 自动管理', tone: 'success' },
      { title: '权限模式', detail: '写入、apply、恢复前都需要用户确认。', control: '写入需批准', tone: 'warning' },
    ],
  },
  code: {
    eyebrow: '代码阅读体验',
    title: '代码预览主题',
    summary: '补丁差异、行号和长行折叠都在这里统一管理。',
    metrics: [
      { label: '浅色代码', value: 'GitHub Light' },
      { label: '深色代码', value: 'GitHub Dark', tone: 'success' },
      { label: '行号', value: '显示' },
    ],
    rows: [
      { title: '浅色代码主题', detail: '浅色模式下代码块使用高对比主题，避免玻璃背景影响阅读。', control: 'GitHub Light' },
      { title: '深色代码主题', detail: '深色模式下代码块保持清晰边界和稳定行高。', control: 'GitHub Dark', tone: 'success' },
      { title: '长行自动换行', detail: '补丁和日志过长时自动换行，减少横向滚动。', control: '开启' },
    ],
  },
  model: {
    eyebrow: '模型与密钥边界',
    title: '模型提供方',
    summary: 'API 密钥只显示配置状态，不在界面回显明文。',
    metrics: [
      { label: '连接方式', value: 'OpenAI 兼容' },
      { label: '密钥状态', value: '加载中...', tone: 'warning' },
      { label: '默认模型', value: '用户选择' },
    ],
    rows: [
      { title: '提供方', detail: '模型供应商和 Base URL 由本地配置管理。', control: 'OpenAI 兼容' },
      { title: 'API 密钥', detail: '只显示是否已配置，保存后立即清空输入框。', control: '仅状态可见', tone: 'warning' },
      { title: '模型选择', detail: '聊天时使用当前选择的模型，不自动切换到未知供应商。', control: '手动选择' },
    ],
  },
  permission: {
    eyebrow: '安全批准链路',
    title: '权限中心',
    summary: '集中查看待批准请求、写入门禁和审计记录，不提供越权入口。',
    metrics: [
      { label: '待批准请求', value: '人工处理', tone: 'warning' },
      { label: '写入门禁', value: '强制开启', tone: 'success' },
      { label: '审计记录', value: '全程保留' },
    ],
    rows: [
      { title: '待批准请求', detail: '工具写入、补丁 apply 和恢复动作进入队列后等待用户确认。', control: '查看队列', tone: 'warning' },
      { title: '写入门禁', detail: '所有写入、apply 和恢复动作都必须等待用户确认。', control: '不可绕过', tone: 'success' },
      { title: '审计记录', detail: '每次批准、拒绝和执行结果都进入审计链路。', control: '只读追踪' },
    ],
  },
  patch: {
    eyebrow: '写入前审查',
    title: '补丁审查',
    summary: '在写入前阅读 diff、风险摘要和批准状态，避免看不见的文件改动。',
    metrics: [
      { label: '补丁预览', value: '多文件 diff' },
      { label: '风险摘要', value: '逐项解释', tone: 'warning' },
      { label: '批准写入', value: '等待确认', tone: 'success' },
    ],
    rows: [
      { title: '补丁预览', detail: '按文件展示新增、删除和上下文，不在这里直接写入。', control: '只读预览' },
      { title: '风险摘要', detail: '标记权限、路径、敏感信息和测试影响。', control: '人工复核', tone: 'warning' },
      { title: '批准写入', detail: '只有用户确认后，补丁才允许进入写入流程。', control: '批准门控', tone: 'success' },
    ],
  },
  audit: {
    eyebrow: '状态与恢复',
    title: '审计诊断',
    summary: '阻断、警告、提示和下一步建议按优先级展示。',
    metrics: [
      { label: '审计时间线', value: '权限与工具链路' },
      { label: '诊断中心', value: '阻断优先', tone: 'warning' },
      { label: '恢复建议', value: '人工确认', tone: 'success' },
    ],
    rows: [
      { title: '审计时间线', detail: '按时间记录权限请求、工具结果、测试反馈和恢复动作。', control: '只读查看' },
      { title: '诊断中心', detail: '阻断、警告、提示分层显示，先处理高风险项。', control: '优先级' },
      { title: '恢复建议', detail: '只给出可验证下一步，不自动执行修复。', control: '等待确认', tone: 'warning' },
    ],
  },
  validation: {
    eyebrow: '只读发布门禁',
    title: '验证发布',
    summary: '这里只展示检查结果，不执行推送、发布或打标签。',
    metrics: [
      { label: '验证门禁', value: '等待结果', tone: 'warning' },
      { label: '测试反馈', value: '结构化回填' },
      { label: '发布准备', value: '只读检查', tone: 'success' },
    ],
    rows: [
      { title: '验证门禁', detail: '汇总测试、构建、文档和中文 UI 检查结果。', control: '只读评估' },
      { title: '测试反馈', detail: '展示白名单测试回填，不接受任意 shell 命令。', control: '白名单' },
      { title: '发布准备', detail: '检查发布准备度，但不执行推送、发布或打标签。', control: '人工决定', tone: 'warning' },
    ],
  },
  collaboration: {
    eyebrow: '上下文与团队',
    title: '智能协作',
    summary: '统一展示记忆、角色分工和队列状态，不自动派发写入任务。',
    metrics: [
      { label: '记忆索引', value: '决策与失败' },
      { label: '多 Agent 团队', value: '规划/执行/审查', tone: 'success' },
      { label: '多任务队列', value: '排队可见', tone: 'warning' },
    ],
    rows: [
      { title: '记忆索引', detail: '汇总项目画像、代码地图、决策记忆和失败记忆。', control: '只读检索' },
      { title: '多 Agent 团队', detail: '显示 Planner、Builder、Reviewer 的职责边界。', control: '角色分工', tone: 'success' },
      { title: '多任务队列', detail: '展示排队、暂停和恢复状态，写入仍需用户确认。', control: '队列状态', tone: 'warning' },
    ],
  },
  skills: {
    eyebrow: '能力目录',
    title: '技能管理',
    summary: '查看可用技能、启用状态和安全边界，技能变更仍需明确批准。',
    metrics: [
      { label: '内置技能', value: '只读可见', tone: 'success' },
      { label: '用户技能', value: '本地管理' },
      { label: '启用状态', value: '人工确认', tone: 'warning' },
    ],
    rows: [
      { title: '技能来源', detail: '区分内置技能、项目技能和用户技能，避免混淆能力边界。', control: '来源分层' },
      { title: '启用策略', detail: '技能只在匹配任务时进入候选，不自动修改项目文件。', control: '按需候选', tone: 'success' },
      { title: '安全边界', detail: '涉及写入、联网、执行命令的技能必须经过权限门禁。', control: '门禁保护', tone: 'warning' },
    ],
  },
  agents: {
    eyebrow: '角色边界',
    title: '子智能体',
    summary: '展示子智能体角色、工具范围和交接状态，避免自审自批。',
    metrics: [
      { label: '默认角色', value: '规划/执行/审查' },
      { label: '工具范围', value: '按角色限制', tone: 'success' },
      { label: '人工接管', value: '随时可控', tone: 'warning' },
    ],
    rows: [
      { title: '默认子智能体', detail: '规划、执行、审查分工展示清楚，同一任务不允许自我批准。', control: '角色隔离', tone: 'success' },
      { title: '工具范围', detail: '每个角色只展示与职责匹配的工具能力。', control: '最小权限' },
      { title: '人工接管', detail: '长任务、失败恢复和写入前都保留用户接管位置。', control: '可暂停', tone: 'warning' },
    ],
  },
  mcp: {
    eyebrow: '外部能力连接',
    title: 'MCP 服务器',
    summary: '查看 MCP 服务器配置、连接状态和工具授权，不自动连接未知服务。',
    metrics: [
      { label: '服务器', value: '配置可见' },
      { label: '连接状态', value: '只读检查', tone: 'success' },
      { label: '工具授权', value: '逐项批准', tone: 'warning' },
    ],
    rows: [
      { title: '服务器列表', detail: '按名称、来源和状态展示 MCP 服务器，不自动导入外部配置。', control: '只读列表' },
      { title: '工具授权', detail: 'MCP 工具执行前仍走权限分类和用户确认。', control: '逐项门禁', tone: 'warning' },
      { title: '连接状态', detail: '显示在线、离线和错误提示，避免静默失败。', control: '状态检测', tone: 'success' },
    ],
  },
  plugins: {
    eyebrow: '扩展生态',
    title: '插件管理',
    summary: '集中查看已安装插件、发现入口和更新状态，不自动安装或升级。',
    metrics: [
      { label: '已安装', value: '本地插件' },
      { label: '发现插件', value: '人工选择' },
      { label: '更新检查', value: '只读提示', tone: 'warning' },
    ],
    rows: [
      { title: '已安装插件', detail: '展示插件名称、版本和启用状态，避免隐藏能力。', control: '本地列表' },
      { title: '发现插件', detail: '发现结果只作为候选展示，安装前必须由用户确认。', control: '手动安装', tone: 'warning' },
      { title: '更新检查', detail: '显示可用更新和变更摘要，不自动下载或替换。', control: '只读提醒' },
    ],
  },
  commands: {
    eyebrow: '命令目录',
    title: '命令管理',
    summary: '管理可调用命令的说明、参数和权限边界，命令执行仍需门禁。',
    metrics: [
      { label: '命令文件', value: 'Markdown' },
      { label: '调用方式', value: '/command' },
      { label: '写入边界', value: '需批准', tone: 'warning' },
    ],
    rows: [
      { title: '命令文件', detail: '命令说明以结构化文档展示，便于审查来源和用途。', control: '文档化' },
      { title: '调用方式', detail: '聊天中通过明确命令触发，不从普通文本里静默执行。', control: '显式调用', tone: 'success' },
      { title: '写入边界', detail: '命令涉及文件写入、删除、发布或外部调用时必须进入批准队列。', control: '权限门禁', tone: 'warning' },
    ],
  },
  index: {
    eyebrow: '项目知识',
    title: '索引库',
    summary: '展示项目画像、代码地图和记忆索引，让上下文可查、可追溯。',
    metrics: [
      { label: '项目画像', value: '结构摘要' },
      { label: '代码地图', value: '模块索引', tone: 'success' },
      { label: '记忆检索', value: '只读查询' },
    ],
    rows: [
      { title: '项目画像', detail: '概括产品目标、技术栈、安全规则和当前阶段。', control: '画像摘要' },
      { title: '代码地图', detail: '按模块记录入口文件、API 和测试位置，方便快速定位。', control: '模块导航', tone: 'success' },
      { title: '记忆检索', detail: '检索决策、失败和偏好记忆，结果保持只读。', control: '安全检索' },
    ],
  },
  usage: {
    eyebrow: '使用洞察',
    title: '使用统计',
    summary: '以只读方式查看会话、消息、Token 和模型使用趋势。',
    metrics: [
      { label: 'Token 用量', value: '趋势统计' },
      { label: '会话数量', value: '近期汇总' },
      { label: '模型占比', value: '可视化' },
    ],
    rows: [
      { title: 'Token 用量', detail: '按时间范围展示消耗趋势，辅助控制预算。', control: '趋势图' },
      { title: '会话数量', detail: '统计任务、消息和活跃天数，帮助理解使用节奏。', control: '只读统计' },
      { title: '模型占比', detail: '显示常用模型比例，不自动切换模型。', control: '手动选择', tone: 'warning' },
    ],
  },
  diagnostics: {
    eyebrow: '本地诊断',
    title: '诊断与反馈',
    summary: '崩溃与启动诊断默认仅保存在本机，上传需要你主动同意。',
    metrics: [
      { label: '收集', value: '本地默认', tone: 'success' },
      { label: '上传', value: '默认关闭', tone: 'warning' },
      { label: '更新检查', value: '手动/关闭' },
    ],
    rows: [
      { title: '诊断目录', detail: '可复制脱敏摘要或打开本地日志目录。', control: '本机' },
      { title: '自动上传', detail: '当前版本不自动上传崩溃信息。', control: '关闭', tone: 'success' },
    ],
  },
  guide: {
    eyebrow: '上手路径',
    title: '引导中心',
    summary: '把新用户需要的工作区、权限、安全和下一步操作整理成清晰路径。',
    metrics: [
      { label: '新手引导', value: '分步完成' },
      { label: '安全规则', value: '始终可见', tone: 'success' },
      { label: '下一步建议', value: '人工决定', tone: 'warning' },
    ],
    rows: [
      { title: '新手引导', detail: '从选择工作区、输入任务到查看结果，按步骤引导用户完成。', control: '分步引导' },
      { title: '安全规则', detail: '解释权限批准、审计记录和写入前预览，降低误操作风险。', control: '安全说明', tone: 'success' },
      { title: '下一步建议', detail: '给出可选建议，但不自动进入新阶段或执行危险操作。', control: '等待选择', tone: 'warning' },
    ],
  },
};
