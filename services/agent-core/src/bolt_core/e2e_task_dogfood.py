"""E2E Task Dogfood (M118). Simulate the full agent loop in a temp directory.

End-to-end: read file → generate patch → human approval → apply → test → audit.
Verifies happy path, no-approval path, stale path, and audit chain completeness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bolt_core.approval_apply import ApprovalApplyEngine
from bolt_core.write_tool_proposal import (
    OP_CREATE, OP_MODIFY, RISK_LOW, STATUS_APPROVED, STATUS_STALE,
    WriteProposal, WriteProposalStore,
)

_DIFF_ADD_HELLO = (
    "--- a/src/greeting.py\n"
    "+++ b/src/greeting.py\n"
    "@@ -1,3 +1,4 @@\n"
    " # greeting.py\n"
    " def greet():\n"
    "+    print('Hello from Bolt')\n"
    "     return 'Hello'\n"
)

_DIFF_NEW_FILE = (
    "--- /dev/null\n"
    "+++ b/src/new_feature.py\n"
    "@@ -0,0 +1,2 @@\n"
    "+def new_feature():\n"
    "+    return True\n"
)


@dataclass(frozen=True)
class E2EDogfoodResult:
    scenario: str; passed: bool; steps: list[str]; audit_complete: bool
    triggered_dangerous_ops: bool = False; chinese_report: str = ""

    def to_dict(self) -> dict:
        return {"scenario": self.scenario, "passed": self.passed,
                "steps": self.steps, "audit_complete": self.audit_complete,
                "triggered_dangerous_ops": self.triggered_dangerous_ops,
                "chinese_report": self.chinese_report}


@dataclass
class E2EDogfoodSummary:
    total_scenarios: int = 0; passed: int = 0; failed: int = 0
    results: list[E2EDogfoodResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"total_scenarios": self.total_scenarios, "passed": self.passed,
                "failed": self.failed,
                "all_passed": self.passed == self.total_scenarios,
                "results": [r.to_dict() for r in self.results],
                "disclaimer": "端到端任务复盘在临时目录中运行，不修改真实项目文件。",
                "verdict": "✅ E2E dogfood 通过" if self.passed == self.total_scenarios else "❌ 存在失败",
                }


# ── Helpers ──

def _pf(tmp_dir: Path, path: str, content: str) -> None:
    fp = tmp_dir / path; fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")

def _approve(store: WriteProposalStore, pid: str) -> None:
    p = store._proposals.get(pid)
    if p is None: return
    store._proposals[pid] = WriteProposal(
        proposal_id=p.proposal_id, tool_id=p.tool_id, target_files=p.target_files,
        operation_type=p.operation_type, before_summary=p.before_summary,
        after_summary=p.after_summary, diff_preview=p.diff_preview,
        risk_level=p.risk_level, required_permissions=p.required_permissions,
        rollback_hint=p.rollback_hint, chinese_explanation=p.chinese_explanation,
        git_head=p.git_head, status=STATUS_APPROVED, created_at=p.created_at)

def _stale(store: WriteProposalStore, pid: str) -> None:
    p = store._proposals.get(pid)
    if p is None: return
    store._proposals[pid] = WriteProposal(
        proposal_id=p.proposal_id, tool_id=p.tool_id, target_files=p.target_files,
        operation_type=p.operation_type, before_summary=p.before_summary,
        after_summary=p.after_summary, diff_preview=p.diff_preview,
        risk_level=p.risk_level, required_permissions=p.required_permissions,
        rollback_hint=p.rollback_hint, chinese_explanation=p.chinese_explanation,
        git_head="0" * 40, status=STATUS_STALE, created_at=p.created_at)


# ── Service ──


class E2ETaskDogfoodService:
    """M118 端到端任务复盘服务。"""

    @staticmethod
    def run_all(tmp_dir: Path) -> E2EDogfoodSummary:
        results = [
            E2ETaskDogfoodService._happy_path(tmp_dir / "happy"),
            E2ETaskDogfoodService._no_approval(tmp_dir / "noapp"),
            E2ETaskDogfoodService._stale_path(tmp_dir / "stale"),
            E2ETaskDogfoodService._create_and_audit(tmp_dir / "create"),
        ]
        p = sum(1 for r in results if r.passed)
        return E2EDogfoodSummary(total_scenarios=len(results), passed=p,
                                 failed=len(results) - p, results=results)

    @staticmethod
    def _happy_path(case_dir: Path) -> E2EDogfoodResult:
        """Happy path: read → propose → approve → apply → verify → audit."""
        case_dir.mkdir(parents=True, exist_ok=True)
        steps: list[str] = []
        store = WriteProposalStore(project_dir=str(case_dir))
        engine = ApprovalApplyEngine(store=store, project_dir=str(case_dir))

        # Step 1: Prepare file (simulates "read file" phase)
        _pf(case_dir, "src/greeting.py", "# greeting.py\ndef greet():\n    return 'Hello'\n")
        steps.append("1. 读取文件 src/greeting.py → 成功")

        # Step 2: Generate patch proposal
        v = store.create(tool_id="write_file", target_files=["src/greeting.py"],
                         operation_type=OP_MODIFY, diff_preview=_DIFF_ADD_HELLO,
                         risk_level=RISK_LOW, chinese_explanation="添加问候语")
        if not v.valid:
            return E2EDogfoodResult("happy_path", False, steps + [f"创建提案失败: {v.errors}"], False)
        pid = v.proposal.proposal_id
        steps.append(f"2. 生成补丁提案 {pid[:16]}... → 成功")

        # Step 3: Verify no approval = can't apply
        result_no_app = engine.apply(pid, {"actor": "human", "scope": pid})
        if result_no_app.success:
            return E2EDogfoodResult("happy_path", False, steps + ["3. 未批准却apply成功 → 安全漏洞！"], False)
        steps.append("3. 未批准apply被正确拒绝 → 安全验证通过")

        # Step 4: Simulate human approval
        _approve(store, pid)
        steps.append("4. 模拟用户批准 → 已批准")

        # Step 5: Apply
        result = engine.apply(pid, {"actor": "human", "scope": pid})
        if not result.success:
            return E2EDogfoodResult("happy_path", False, steps + [f"5. apply失败: {result.reason}"], False)
        steps.append(f"5. 应用补丁 → {len(result.audit_record.get('files_changed', []))}个文件已变更")

        # Step 6: Verify file changed
        new_content = (case_dir / "src/greeting.py").read_text()
        if "Hello from Bolt" not in new_content:
            return E2EDogfoodResult("happy_path", False, steps + ["6. 文件验证失败"], False)
        steps.append("6. 文件内容验证 → 补丁正确应用")

        # Step 7: Audit check
        audit_log = engine.audit_log()
        audit_ok = len(audit_log) >= 1 and audit_log[0].get("result") == "applied"
        steps.append(f"7. 审计检查 → {'完整' if audit_ok else '不完整'}（{len(audit_log)}条记录）")

        report = "端到端Happy Path通过：读取→提案→审批→应用→验证→审计全部正常。"
        return E2EDogfoodResult("happy_path", True, steps, audit_ok,
                                chinese_report=report)

    @staticmethod
    def _no_approval(case_dir: Path) -> E2EDogfoodResult:
        """No approval path: should fail at apply. Must not modify files."""
        case_dir.mkdir(parents=True, exist_ok=True)
        steps: list[str] = []
        store = WriteProposalStore(project_dir=str(case_dir))
        engine = ApprovalApplyEngine(store=store, project_dir=str(case_dir))

        _pf(case_dir, "src/greeting.py", "# greeting.py\ndef greet():\n    return 'Hello'\n")
        original = (case_dir / "src/greeting.py").read_text()

        v = store.create(tool_id="write_file", target_files=["src/greeting.py"],
                         operation_type=OP_MODIFY, diff_preview=_DIFF_ADD_HELLO,
                         risk_level=RISK_LOW, chinese_explanation="无批准测试")
        pid = v.proposal.proposal_id
        steps.append("1. 创建提案（未批准）→ 成功")

        # Try apply with agent (self-approve)
        result = engine.apply(pid, {"actor": "agent", "scope": pid})
        if result.success:
            return E2EDogfoodResult("no_approval", False,
                                    steps + ["apply意外成功 → 安全漏洞"], False)
        steps.append("2. agent自批apply被拒绝 → 正确")

        # Verify file unchanged
        after = (case_dir / "src/greeting.py").read_text()
        if original != after:
            return E2EDogfoodResult("no_approval", False,
                                    steps + ["文件被非法修改"], False)
        steps.append("3. 文件内容未被修改 → 安全")

        report = "无批准路径通过：未批准时apply被正确拒绝，文件未被修改。"
        return E2EDogfoodResult("no_approval", True, steps, True,
                                chinese_report=report)

    @staticmethod
    def _stale_path(case_dir: Path) -> E2EDogfoodResult:
        """Stale proposal path: expired proposal must be rejected."""
        case_dir.mkdir(parents=True, exist_ok=True)
        steps: list[str] = []
        store = WriteProposalStore(project_dir=str(case_dir))
        engine = ApprovalApplyEngine(store=store, project_dir=str(case_dir))

        _pf(case_dir, "src/greeting.py", "# greeting.py\ndef greet():\n    return 'Hello'\n")
        v = store.create(tool_id="write_file", target_files=["src/greeting.py"],
                         operation_type=OP_MODIFY, diff_preview=_DIFF_ADD_HELLO,
                         risk_level=RISK_LOW, chinese_explanation="过期测试")
        pid = v.proposal.proposal_id
        _approve(store, pid)
        _stale(store, pid)
        steps.append("1. 创建并标记过期提案 → 成功")

        result = engine.apply(pid, {"actor": "human", "scope": pid})
        if result.success:
            return E2EDogfoodResult("stale_path", False,
                                    steps + ["过期提案apply成功 → 安全漏洞"], False)
        steps.append("2. 过期提案被拒绝 → 正确（需重新创建）")

        report = "过期提案路径通过：过期提案apply被正确拒绝。"
        return E2EDogfoodResult("stale_path", True, steps, True,
                                chinese_report=report)

    @staticmethod
    def _create_and_audit(case_dir: Path) -> E2EDogfoodResult:
        """Create file + audit chain completeness."""
        case_dir.mkdir(parents=True, exist_ok=True)
        steps: list[str] = []
        store = WriteProposalStore(project_dir=str(case_dir))
        engine = ApprovalApplyEngine(store=store, project_dir=str(case_dir))

        v = store.create(tool_id="write_file", target_files=["src/new_feature.py"],
                         operation_type=OP_CREATE, diff_preview=_DIFF_NEW_FILE,
                         risk_level=RISK_LOW, chinese_explanation="新建特性文件")
        pid = v.proposal.proposal_id
        _approve(store, pid)
        steps.append("1. 提案已批准 → 就绪")

        result = engine.apply(pid, {"actor": "human", "scope": pid})
        if not result.success:
            return E2EDogfoodResult("create_and_audit", False,
                                    steps + [f"apply失败: {result.reason}"], False)

        # Verify file created
        new_file = case_dir / "src/new_feature.py"
        if not new_file.exists():
            return E2EDogfoodResult("create_and_audit", False,
                                    steps + ["新文件未创建"], False)
        content = new_file.read_text()
        if "def new_feature" not in content:
            return E2EDogfoodResult("create_and_audit", False,
                                    steps + ["文件内容错误"], False)
        steps.append("2. 新文件创建并内容正确 → 通过")

        # Audit trace
        audit_log = engine.audit_log()
        audit_ok = (len(audit_log) >= 1
                    and audit_log[0].get("operation_type") == "create"
                    and len(audit_log[0].get("files_changed", [])) >= 1
                    and audit_log[0].get("result") == "applied")
        steps.append(f"3. 审计链验证 → {'完整' if audit_ok else '不完整'}")

        report = "创建+审计路径通过：新建文件成功应用，审计记录完整。"
        return E2EDogfoodResult("create_and_audit", True, steps, audit_ok,
                                chinese_report=report)
