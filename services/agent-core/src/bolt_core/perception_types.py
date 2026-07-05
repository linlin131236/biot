from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkspaceProfile:
    root_path: str
    name: str
    package_manager: str | None = None
    languages: list[str] = field(default_factory=list)
    manifests: list[str] = field(default_factory=list)
    entry_files: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    build_commands: list[str] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    truncated: bool = False


@dataclass(frozen=True)
class FileIndexEntry:
    path: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileIndex:
    entries: list[FileIndexEntry] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    truncated: bool = False


@dataclass(frozen=True)
class IntentClassification:
    category: str
    confidence: float
    signals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RuntimeObservation:
    status: str = "manual"
    ports: list[int] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UiObservation:
    status: str = "manual"
    workspace_path: str = ""
    current_file: str | None = None
    selection: str | None = None


@dataclass(frozen=True)
class SchedulerDecision:
    priority: str
    task: str
    status: str


@dataclass(frozen=True)
class PerceptionSnapshot:
    workspace_profile: WorkspaceProfile
    file_index: FileIndex
    intent: IntentClassification
    runtime: RuntimeObservation
    ui: UiObservation
    scheduler: list[SchedulerDecision]


def dataclass_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
