"""Read-only recovery policy. Describes manual recovery steps, never auto-executes."""
from __future__ import annotations


class RecoveryPolicyService:
    """Produces a human-readable recovery policy for known failure scenarios.
    Does NOT execute any rollback, reset, delete, or recovery action.
    """

    def list_scenarios(self) -> dict:
        scenarios = [
            # ── 审计损坏 ──
            _scenario(
                "audit_corrupt",
                "审计文件损坏",
                "审计完整性",
                "high",
                "execution-audit.json 文件 JSON 格式损坏，无法被 ExecutionAuditStore 正常加载。可能原因：手动编辑错误、磁盘写入中断、并发写入冲突。",
                [
                    "1. 检查文件是否可读：确认 execution-audit.json 文件存在且不是空文件。",
                    "2. 尝试 JSON 修复：用在线 JSON 校验工具定位语法错误位置。如 syntax error 在第 N 行，用编辑器修复对应位置。",
                    "3. 从备份恢复：如果配置了 .bolt/ 备份策略，从最近的备份文件恢复。",
                    "4. 手动重建：如无法修复，可删除损坏文件，系统将自动创建空的审计文件。注意：这将丢失所有审计历史。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "禁止直接执行 rm/del 删除审计文件，除非已确认无法修复。",
                    "删除审计文件前必须告知用户，获取明确许可。",
                ],
            ),
            _scenario(
                "audit_missing",
                "审计文件缺失",
                "审计完整性",
                "medium",
                "execution-audit.json 文件不存在。可能是首次运行、路径配置错误、或文件被误删除。",
                [
                    "1. 检查环境变量 BOLT_EXECUTION_AUDIT_PATH 是否被错误设置。",
                    "2. 如果这是首次运行，系统将自动创建空的审计文件，无需处理。",
                    "3. 如果之前有审计数据但文件丢失，检查回收站或备份。",
                ],
                auto_recovery_possible=True,
                warnings=[
                    "自动重建不会恢复丢失的审计历史数据。",
                ],
            ),
            # ── 发布失败 ──
            _scenario(
                "release_push_rejected",
                "Git push 被远程拒绝",
                "发布失败",
                "high",
                "git push 到 origin/main 被拒绝。可能原因：远程有新提交、分支保护规则、网络问题。",
                [
                    "1. 先运行 git fetch origin 查看远程最新状态。",
                    "2. 如果远程有新提交：git pull --rebase origin main 后重新检查冲突。",
                    "3. 如果是分支保护规则：在 GitHub/GitLab 设置中临时解除保护，或通过 PR/MR 流程提交。",
                    "4. 如果是网络问题：检查 VPN、代理、SSH key 配置。",
                    "5. 不要使用 git push --force，除非用户明确确认。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "禁止自动执行 git push --force。",
                    "禁止跳过 CI/CD 检查门（如果配置了）。",
                ],
            ),
            _scenario(
                "release_tag_conflict",
                "Git tag 冲突",
                "发布失败",
                "medium",
                "尝试创建的 tag 已存在或与已有 tag 冲突。",
                [
                    "1. 运行 git tag -l 查看已存在的 tag。",
                    "2. 如果 tag 已存在且内容正确，无需重新创建。",
                    "3. 如果 tag 内容错误，在用户确认后执行：git tag -d <tagname> && git push origin :refs/tags/<tagname>。",
                    "4. 重新创建正确的 tag：git tag -a vX.Y.Z -m '...' && git push origin vX.Y.Z。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "禁止自动删除远程 tag。",
                    "删除 tag 操作不可逆，必须在用户明确确认后由人工执行。",
                ],
            ),
            # ── 权限误操作 ──
            _scenario(
                "perm_misapproval",
                "误批准危险命令",
                "权限误操作",
                "critical",
                "在 PermissionGate 中误批准了危险权限请求（如文件删除、shell 命令执行）。命令可能已经执行，或仍在等待队列中。",
                [
                    "1. 立即检查执行结果：查看执行审计时间线，确认命令是否已执行及其结果。",
                    "2. 如果命令已执行且造成了破坏：使用 git diff / git log 检查被修改的文件。",
                    "3. 通过 git checkout 或 git revert 恢复被修改的文件。",
                    "4. 如果命令在队列中但尚未执行：在 ExecutionQueuePanel 中 reject 该队列项。",
                    "5. 复盘：在 project-state.md 中记录此次误操作的发生原因和修复结果。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "PermissionGate 批准是人工操作，无法自动回滚。",
                    "不要为了快速修复而绕过 PermissionGate 执行更多危险命令。",
                ],
            ),
            _scenario(
                "perm_gate_bypass",
                "怀疑 PermissionGate 被绕过",
                "权限误操作",
                "critical",
                "发现可能存在绕过 PermissionGate 直接执行的路径。需要立即验证并加固。",
                [
                    "1. 检查执行审计日志：搜索是否有未经过 pending->approve 流程的执行记录。",
                    "2. 检查代码中的执行路径：确认所有 shell/file/network 操作都经过 PermissionGate。",
                    "3. 检查 check-architecture.mjs 扫描结果：确认没有新增的 shell 执行路径。",
                    "4. 临时措施：在确认安全前，暂停 Agent Loop 运行。",
                    "5. 修复后：更新架构白名单，补充验证测试。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "这属于安全红线，必须立即处理，不得延迟。",
                    "在确认修复前，不继续推进后续 milestone。",
                ],
            ),
            # ── 任务中断 ──
            _scenario(
                "task_interrupted",
                "Agent 任务意外中断",
                "任务中断",
                "medium",
                "Agent loop 或长任务因进程崩溃、断电、超时而中断。任务状态可能处于 pending/running 中间态。",
                [
                    "1. 检查 Agent Core 进程状态：确认服务是否仍在运行。",
                    "2. 重启 Agent Core 服务：uv run uvicorn bolt_core.app:app --reload。",
                    "3. 在 Bolt Desktop 中查看未完成目标：目标列表会显示 paused/failed 状态。",
                    "4. 对于 paused 目标：点击「恢复」继续执行。",
                    "5. 对于 failed 目标：查看执行审计时间线了解失败原因，修复后重新创建目标。",
                ],
                auto_recovery_possible=True,
                warnings=[
                    "恢复前先检查执行审计日志，确认中断时没有留下脏状态。",
                    "恢复时不要跳过 PermissionGate 的权限检查。",
                ],
            ),
            _scenario(
                "process_crash",
                "Agent Core 进程崩溃",
                "任务中断",
                "high",
                "Agent Core (uvicorn/FastAPI) 进程异常退出。前端无法连接后端服务。",
                [
                    "1. 检查端口占用：确认 8000 端口是否被其他进程占用。",
                    "2. 重新启动服务：在项目根目录运行：cd services/agent-core && uv run uvicorn bolt_core.app:app --host 0.0.0.0 --port 8000 --reload。",
                    "3. 检查审计文件完整性：重启后查看 /execution-audit/integrity 诊断结果。",
                    "4. 如果审计文件因崩溃损坏：参考「审计文件损坏」恢复场景。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "不要在崩溃后立即删除审计文件。先尝试诊断和修复。",
                ],
            ),
            # ── 数据/文档不一致 ──
            _scenario(
                "docs_inconsistent",
                "项目文档与代码不一致",
                "数据损坏",
                "low",
                "project-state.md 记载的 milestone 与实际的代码/phase gate 不一致。可能原因：文档更新遗漏、合并冲突。",
                [
                    "1. 对比 project-state.md 的「已完成到：M{n}」与 docs/phase-*-review-gate.md 的最新编号。",
                    "2. 如果 project-state.md 落后：更新「已完成到」字段到实际最新 milestone。",
                    "3. 如果 phase gate 文件缺失：找到该 milestone 的 review gate 文档或重新编写。",
                    "4. 运行发布准备度检查 (/release-readiness) 和本地发布清单 (/local-release-checklist) 确认一致性。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "不要删除旧 phase gate 文档，它们属于审计历史。",
                ],
            ),
            _scenario(
                "review_gate_missing",
                "Phase review gate 文件缺失",
                "数据损坏",
                "medium",
                "某个已完成 milestone 的 docs/phase-{n}-review-gate.md 文件缺失。可能被误删除或从未创建。",
                [
                    "1. 确认该 milestone 是否确实已完成：查看 git log 找到对应的 commit。",
                    "2. 如果该 milestone 已完成但 gate 文件缺失：参考已有 gate 文件格式重建。",
                    "3. 如果该 milestone 未完成：创建空 gate 文件并标记为「进行中」。",
                ],
                auto_recovery_possible=False,
                warnings=[
                    "不要伪造审查通过记录。gate 文件内容必须真实反映审查结果。",
                ],
            ),
        ]

        categories: dict[str, list[dict]] = {}
        for s in scenarios:
            cat = s["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(s)

        return {
            "scenarios": scenarios,
            "categories": categories,
            "total": len(scenarios),
            "disclaimer": "本恢复策略为只读人工参考，不自动执行任何回滚、重置、删除或修复操作。所有恢复步骤需由用户在终端人工执行。",
        }


def _scenario(
    code: str,
    title: str,
    category: str,
    severity: str,
    description: str,
    steps: list[str],
    auto_recovery_possible: bool,
    warnings: list[str],
) -> dict:
    severity_labels = {
        "critical": "🔴 严重",
        "high": "🟠 高危",
        "medium": "🟡 中等",
        "low": "🟢 低",
    }
    return {
        "code": code,
        "title": title,
        "category": category,
        "severity": severity,
        "severity_label": severity_labels.get(severity, severity),
        "description": description,
        "recovery_steps": steps,
        "auto_recovery_possible": auto_recovery_possible,
        "auto_recovery_label": "可自动恢复" if auto_recovery_possible else "需人工介入",
        "warnings": warnings,
    }
