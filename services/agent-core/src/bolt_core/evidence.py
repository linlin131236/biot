import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    step: int
    action: str
    result: str
    output: str
    files_changed: list[str]
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class EvidenceLog:
    def __init__(self) -> None:
        self._entries: list[Evidence] = []

    @property
    def entries(self) -> list[Evidence]:
        return list(self._entries)

    def record(self, step: int, action: str, result: str, output: str, files_changed: list[str] | None = None) -> Evidence:
        entry = Evidence(step=step, action=action, result=result, output=output, files_changed=files_changed or [])
        self._entries.append(entry)
        return entry

    def recent_summary(self, max_entries: int = 5) -> list[Evidence]:
        if max_entries >= len(self._entries):
            return list(self._entries)
        return list(self._entries[-max_entries:])
