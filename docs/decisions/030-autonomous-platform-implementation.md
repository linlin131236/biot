# 030-autonomous-platform-implementation.md

**Date:** 2026-07-06
**Status:** Implemented

## Context

Bolt needs autonomous platform capabilities: goal-driven execution, multi-turn conversation, vector memory, skills, delegation, MoA, checkpoints, and review gates.

## Decisions

### D1: GoalPersistence 拆分为独立文件
goal.py 不再有 write_text → 不需要 architecture write 白名单。GoalPersistence 独立为 goal_persistence.py，加入白名单（元数据持久化基础设施，与 file_writer.py 同类）。

### D2: GoalRunner 无默认完成判定
移除 evidence_type 自动完成。没有 completion_check_fn 时永不 COMPLETED，只靠 budget 停止。加 consecutive_failures (3次→FAILED)。

### D3: BackgroundExecutor 后台线程消费 stdout
防止 PIPE 缓冲区满导致子进程死锁。每进程一个 reader 线程，持续消费到内部 buffer，max_output_size=1MB。

### D4: TerminalService 拆分自 harness.py
harness.py 从 295 行降到 271 行。terminal 相关 5 个方法移入 terminal_service.py。

### D5: ConversationStore 使用 SQLite
轻量级持久化，无需额外依赖。threading.Lock 保护并发。

### D6: ContextCompressor 保护权限/失败证据
压缩旧消息时，permission_pending、step_failed、safety_boundary 等元数据的消息永远不被压缩。

### D7: LocalHashEmbedding 作为确定性 fallback
不依赖 Ollama/OpenAI。Hash embedding 不保证语义排序，但保证确定性。生产环境替换为真实 embedding。

### D8: VectorMemoryStore 拒绝 secret 入库
匹配 sk-XXXX(20+)、AWS AKIA、RSA PRIVATE KEY 模式的内容直接拒绝。

### D9: Skill 不能声明 bypass_permission
manifest 解析时检查 bypass_permission 字段，存在则拒绝加载。

### D10: Delegation reviewer fail → needs_revision
reviewer 任务失败时，被审查的 build 任务自动标记为 needs_revision。

### D11: MoA 默认 dry_run
不自动发起真实 API 调用。budget <= 0 直接拒绝。

### D12: Checkpoint 不含大文件和 secrets
超过 1MB 的文件不快照。输出时 scrub sk- 模式。

### D13: protocol.ts 拆分 protocol-autonomy.ts
主 protocol.ts 保持 248 行（<300 限制）。新增 autonomy 类型放在独立文件。
