# M33 UI Workflow Dogfood + Chinese Desktop Experience

## Goal

Make the Bolt desktop product feel like a real Chinese-first agent workbench: all visible UI text in Chinese, real click-path dogfood tests pass, tool flow (file read/patch) wired through permission gate.

## Scope

- Chinese-ify all user-visible buttons, labels, panel headings, empty-state text, error messages, and sidebar labels.
- Add ToolFlowPanel: file path input, read file button, old/new text inputs, submit patch button.
- Add uiWorkflowDogfood.test.tsx covering click path with Chinese text assertions.
- Update App.test.tsx to match new Chinese button/label names.
- Add M33 docs to the docs quality gate.

## Out of Scope

- New agent intelligence, planner behavior, or model integration.
- Release packaging, signing, or auto-update (M15/M18).
- New `/skills` API behavior.
- Large UI redesign or new design system.
- Changing code variable names, API paths, or test descriptions to Chinese.

## Chinese UI Strategy

All user-visible text must be Chinese. Technical proper nouns may retain English but must be paired with Chinese:

- "Agent Core 状态" (not "Agent Core")
- "工作区" (not "Workspace")
- "核心服务地址" (not "Core URL")
- "API 密钥" (not "API Key")

## Dogfood Click Path

1. 输入任务目标 → 点击"开始任务" → 显示 run id
2. 点击"创建目标" → 显示 goal id + status
3. 输入文件路径 → 点击"读取文件"
4. 输入原文本/新文本 → 点击"提交补丁" → pending_permission
5. 点击"批准" → 文件变更
6. 点击"时间线" → 显示事件数
7. 点击"审查" → 显示通过/失败

## Verification

- `pnpm --filter @bolt/desktop exec vitest run src/uiWorkflowDogfood.test.tsx`
- `cd services/agent-core && .venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `rg "Start Run|Create Goal|Run Step|Refresh Trace|Approve|Reject|Save Model Settings" apps/desktop/src/App.tsx` → must return 0 hits for UI-visible text
