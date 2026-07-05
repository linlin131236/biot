from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bolt_core.failure_memory import ToolFailure
from bolt_core.memory_store import MemoryRecord, MemoryStore


@dataclass(frozen=True)
class FailurePatternProposal:
    path: str
    content: str
    source: str


class DocumentGardener:
    def __init__(self, workspace: str, memory: MemoryStore) -> None:
        self.workspace = workspace
        self.memory = memory

    def proposals(self) -> list[FailurePatternProposal]:
        return [self._proposal(record) for record in self.memory.list(kind="failure", status="active")]

    def _proposal(self, record: MemoryRecord) -> FailurePatternProposal:
        failure = _failure_from_record(record)
        path = failure_pattern_path(self.workspace, failure)
        content = failure_pattern_markdown(failure, source=record.source)
        return FailurePatternProposal(path, content, record.id)


def failure_pattern_path(workspace: str, failure: ToolFailure) -> str:
    tool = _slug(failure.tool)
    operation = _slug(failure.operation)
    parts = [tool]
    if operation and not tool.endswith(operation):
        parts.append(operation)
    parts.append(_slug(failure.failure_class))
    return str(Path(workspace) / "docs" / "failure-patterns" / f"{'-'.join(parts)}.md")


def failure_pattern_markdown(failure: ToolFailure, source: str) -> str:
    title = f"{failure.tool} {failure.operation} {failure.failure_class}"
    return "\n".join([
        f"# {title}",
        "",
        "## Trigger",
        f"- Tool: `{failure.tool}`",
        f"- Operation: `{failure.operation}`",
        f"- Failure class: `{failure.failure_class}`",
        "",
        "## Symptom",
        failure.observable_result,
        "",
        "## Root Cause",
        failure.root_cause,
        "",
        "## Repair",
        failure.repair_result,
        "",
        "## Do Not Repeat",
        f"Do not retry `{failure.operation}` without changing strategy.",
        "",
        "## Source",
        source,
        "",
    ])


def _failure_from_record(record: MemoryRecord) -> ToolFailure:
    return ToolFailure(record.metadata.get("tool", "unknown"), record.scope, record.metadata.get("failure_class", "failure"), record.content, record.metadata.get("root_cause", record.content), record.metadata.get("repair_result", "not_fixed"))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"
