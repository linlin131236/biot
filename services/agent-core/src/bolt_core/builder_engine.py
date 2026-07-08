"""BuilderEngine: executes builder tasks by producing code change proposals.
Extracted from multi_agent_workflow_models.py protocol (M160).

Does NOT write files directly. Produces FileWriteProposal objects
that require PermissionGate approval before application.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bolt_core.file_writer import propose_file_write, FileWriteProposal
from bolt_core.path_guard import PathGuard
from bolt_core.multi_agent_workflow_models import BuilderOutput


@dataclass
class BuilderTask:
    """A builder execution task."""
    task_id: str
    description_cn: str
    target_files: list[str]
    workspace: str
    proposed_changes: dict[str, str] = field(default_factory=dict)  # path -> new_content
    created_at: str = ""


class BuilderEngine:
    """Executes builder tasks by producing code change proposals.
    Does NOT write files, approve permissions, or self-approve.
    """

    def __init__(self, workspace: str | Path | None = None) -> None:
        self._workspace = str(workspace or Path.cwd())
        self._proposals: dict[str, FileWriteProposal] = {}

    def execute_task(self, task: BuilderTask) -> BuilderOutput:
        """Execute a builder task and produce code change proposals.

        Process:
        1. Verify workspace boundary via PathGuard
        2. For each target file, produce a FileWriteProposal
        3. Collect evidence_refs from proposals
        4. Return BuilderOutput (does NOT apply changes)
        """
        evidence_refs: list[str] = []
        code_changes_parts: list[str] = []
        tests_commands: list[str] = []

        guard = PathGuard(self._workspace)

        for file_path in task.target_files:
            check = guard.check(file_path)
            if not check.allowed:
                continue

            proposed_content = task.proposed_changes.get(file_path, "")
            if not proposed_content:
                # Read current content as baseline
                try:
                    proposed_content = check.path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    proposed_content = ""

            proposal = propose_file_write(file_path, proposed_content, self._workspace)
            self._proposals[file_path] = proposal
            evidence_refs.append(f"proposal:{file_path}:{proposal.status}")

            if proposal.status == "pending_review" and proposal.change:
                code_changes_parts.append(
                    f"--- a/{file_path}\n+++ b/{file_path}\n{proposal.change.diff}"
                )

        # Determine test commands based on file types
        for file_path in task.target_files:
            if file_path.endswith(".py"):
                tests_commands.append(f"pytest {file_path}")
            elif file_path.endswith(".ts") or file_path.endswith(".tsx"):
                tests_commands.append(f"vitest run {file_path}")

        code_changes = "\n\n".join(code_changes_parts) if code_changes_parts else "(no changes proposed)"
        tests = "\n".join(tests_commands) if tests_commands else "(no tests specified)"

        return BuilderOutput(
            code_changes=code_changes,
            tests=tests,
            evidence_refs=evidence_refs,
            source_refs=[f"workspace:{self._workspace}"],
        )

    def get_proposal(self, file_path: str) -> FileWriteProposal | None:
        """Get a previously produced proposal."""
        return self._proposals.get(file_path)

    def list_proposals(self) -> dict[str, FileWriteProposal]:
        """List all produced proposals."""
        return dict(self._proposals)
