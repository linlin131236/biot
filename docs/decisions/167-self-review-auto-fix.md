# M167 Decision: Self-Review Auto-Fix

## 决策

Auto-fix 只处理低风险 P2 提案，不直接写文件，不处理 P0/P1。

## 原因

自动修复如果触碰安全问题，会削弱 Reviewer 独立性和人工批准边界。

## 后果

P0/P1/security findings 必须进入人工处理或下一轮 Builder 修复。
