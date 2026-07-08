"""Shared read-only result models for M121-M125 beta reliability gates."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BetaCheck:
    name: str
    passed: bool
    detail: str
    severity: str = "info"


@dataclass
class BetaReviewResult:
    checks: list[BetaCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_step: str = "等待用户复审"
    p1_failures: list[str] = field(default_factory=list)
    all_passed: bool = True

    def __post_init__(self) -> None:
        if not self.p1_failures:
            self.p1_failures = [check.name for check in self.checks if not check.passed and check.severity == "blocking"]
        self.all_passed = len(self.p1_failures) == 0 and all(check.passed for check in self.checks)

    def to_dict(self) -> dict:
        return {
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "detail": check.detail,
                    "severity": check.severity,
                }
                for check in self.checks
            ],
            "total": len(self.checks),
            "passed_count": sum(1 for check in self.checks if check.passed),
            "failed_count": sum(1 for check in self.checks if not check.passed),
            "all_passed": self.all_passed,
            "p1_failures": self.p1_failures,
            "warnings": self.warnings,
            "next_step": self.next_step,
        }


class BetaReadinessBase:
    def __init__(self, project_dir: str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()

    def src(self, module: str) -> Path:
        return self.project_dir / "services/agent-core/src/bolt_core" / f"{module}.py"

    def docs(self, relative: str) -> Path:
        return self.project_dir / "docs" / relative

    def read(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def exists(self, relative: str) -> bool:
        return (self.project_dir / relative).exists()

    def milestone_docs_complete(self, milestone: int) -> bool:
        docs_dir = self.project_dir / "docs"
        return (
            bool(list((docs_dir / "exec-plans/active").glob(f"{milestone}-*.md")))
            and bool(list((docs_dir / "decisions").glob(f"{milestone}-*.md")))
            and (docs_dir / f"phase-{milestone}-review-gate.md").exists()
        )

    def docs_missing(self, start: int, end: int) -> list[str]:
        missing: list[str] = []
        docs_dir = self.project_dir / "docs"
        for milestone in range(start, end + 1):
            if not list((docs_dir / "exec-plans/active").glob(f"{milestone}-*.md")):
                missing.append(f"M{milestone} exec plan")
            if not list((docs_dir / "decisions").glob(f"{milestone}-*.md")):
                missing.append(f"M{milestone} decision")
            if not (docs_dir / f"phase-{milestone}-review-gate.md").exists():
                missing.append(f"M{milestone} review gate")
        return missing

    def scan_files(self, roots: list[Path], patterns: list[str]) -> list[str]:
        hits: list[str] = []
        for root in roots:
            if root.is_file():
                files = [root]
            elif root.is_dir():
                files = [path for path in root.rglob("*") if path.suffix in {".py", ".ts", ".tsx", ".md"}]
            else:
                files = []
            for path in files:
                text = self.read(path)
                for line_no, line in enumerate(text.splitlines(), start=1):
                    for pattern in patterns:
                        if pattern in line:
                            rel = path.relative_to(self.project_dir) if path.is_relative_to(self.project_dir) else path
                            hits.append(f"{rel}:{line_no}:{pattern}")
        return hits


def check(name: str, passed: bool, detail: str, severity: str = "blocking") -> BetaCheck:
    return BetaCheck(name=name, passed=passed, detail=detail, severity=severity if not passed else "info")
