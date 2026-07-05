import json
from dataclasses import asdict, dataclass

from bolt_core.patch_engine import ChangeSet, apply_change_set, build_change_set
from bolt_core.path_guard import PathGuard


@dataclass(frozen=True)
class FileWriteProposal:
    status: str
    change: ChangeSet | None
    error: str | None


def propose_file_write(path: str, proposed_content: str, workspace: str) -> FileWriteProposal:
    check = PathGuard(workspace).check(path)
    if not check.allowed:
        return FileWriteProposal("failed", None, check.reason)
    try:
        original = check.path.read_text(encoding="utf-8")
    except FileNotFoundError:
        original = ""
    except UnicodeDecodeError:
        return FileWriteProposal("failed", None, "binary file not writable")
    except OSError as exc:
        return FileWriteProposal("failed", None, f"read error: {exc}")
    change = build_change_set(str(check.path), original, proposed_content)
    return FileWriteProposal("pending_review", change, None)


def apply_file_write(change_payload: dict) -> tuple[bool, str]:
    change = ChangeSet(**change_payload)
    try:
        decision = apply_change_set(change)
    except OSError as exc:
        return False, f"write error: {exc}"
    return decision.allowed, decision.reason


def change_set_json(change: ChangeSet) -> str:
    return json.dumps(asdict(change))
