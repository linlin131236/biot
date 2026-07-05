from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class ChangeSet:
    path: str
    base_hash: str
    proposed: str
    diff: str
    status: str


@dataclass(frozen=True)
class ApplyDecision:
    allowed: bool
    reason: str


def build_change_set(path: str, original: str, proposed: str) -> ChangeSet:
    return ChangeSet(
        path=path,
        base_hash=_hash(original),
        proposed=proposed,
        diff=_diff(path, original, proposed),
        status="pending_review",
    )


def can_apply_change(change: ChangeSet, current_content: str) -> ApplyDecision:
    if _hash(current_content) != change.base_hash:
        return ApplyDecision(False, "file changed since proposal")
    return ApplyDecision(True, "base hash matches")


def apply_change_set(change: ChangeSet) -> ApplyDecision:
    path = Path(change.path)
    current = path.read_text(encoding="utf-8")
    decision = can_apply_change(change, current)
    if not decision.allowed:
        return decision
    path.write_text(change.proposed, encoding="utf-8")
    return ApplyDecision(True, "change applied")


def _hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _diff(path: str, original: str, proposed: str) -> str:
    lines = unified_diff(
        original.splitlines(),
        proposed.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(lines)
