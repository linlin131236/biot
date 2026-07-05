from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolFailure:
    tool: str
    operation: str
    failure_class: str
    observable_result: str
    root_cause: str
    repair_result: str


@dataclass(frozen=True)
class FailureMemory:
    failure: ToolFailure
    status: str
    do_not_repeat: list[str] = field(default_factory=list)


class FailureStore:
    def __init__(self) -> None:
        self._items: list[FailureMemory] = []

    def record(self, failure: ToolFailure) -> FailureMemory:
        memory = FailureMemory(
            failure=failure,
            status=self._status_for(failure),
            do_not_repeat=[self._constraint_for(failure)],
        )
        self._items.append(memory)
        return memory

    def p0_context(self) -> dict[str, list]:
        unresolved = [item for item in self._items if item.status == "unresolved"]
        return {
            "unresolved_failures": [self._failure_dict(item) for item in unresolved],
            "hard_constraints": self._constraints(unresolved),
        }

    def _status_for(self, failure: ToolFailure) -> str:
        if failure.repair_result == "fixed":
            return "resolved"
        return "unresolved"

    def _constraint_for(self, failure: ToolFailure) -> str:
        return f"Do not retry {failure.operation} without changing strategy"

    def _failure_dict(self, memory: FailureMemory) -> dict[str, str]:
        failure = memory.failure
        return {
            "tool": failure.tool,
            "operation": failure.operation,
            "failure_class": failure.failure_class,
            "observable_result": failure.observable_result,
            "root_cause": failure.root_cause,
            "repair_result": failure.repair_result,
        }

    def _constraints(self, memories: list[FailureMemory]) -> list[str]:
        return [constraint for item in memories for constraint in item.do_not_repeat]
