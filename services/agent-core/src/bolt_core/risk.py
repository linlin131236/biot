from dataclasses import dataclass
from pathlib import PureWindowsPath


@dataclass(frozen=True)
class RiskDecision:
    level: int
    action: str
    reason: str


DANGEROUS_COMMANDS = ("rm -rf /", "del /s /q c:\\", "format ", "git push --force")
BLOCKED_COMMAND_FRAGMENTS = ("| sh", "| bash", "curl ", "Invoke-WebRequest")
SAFE_COMMANDS = ("git", "npm", "pnpm", "pytest", "node", "python", "ls", "cat", "terminal")
SECRET_NAMES = (".env", ".env.local", "id_rsa", "credentials", "secret")


def classify_command(command: str) -> RiskDecision:
    normalized = command.strip().lower()
    executable = normalized.split(maxsplit=1)[0] if normalized else ""
    if _is_destructive_command(normalized):
        return RiskDecision(6, "deny", "destructive command denied")
    if executable in SAFE_COMMANDS:
        return RiskDecision(3, "confirm", "known command execution")
    return RiskDecision(4, "confirm", "unknown command execution")


def classify_background_command(command: str) -> RiskDecision:
    normalized = command.strip().lower()
    if _is_destructive_command(normalized):
        return RiskDecision(6, "deny", "destructive command denied")
    executable = normalized.split(maxsplit=1)[0] if normalized else ""
    if executable in SAFE_COMMANDS:
        return RiskDecision(3, "confirm", "known background command")
    return RiskDecision(4, "confirm", "unknown background command")


def classify_search() -> RiskDecision:
    return RiskDecision(0, "allow", "workspace search")


def classify_web() -> RiskDecision:
    return RiskDecision(0, "allow", "web read-only")


def classify_patch(path: str, workspace: str) -> RiskDecision:
    if _is_secret_path(PureWindowsPath(path)):
        return RiskDecision(6, "deny", "secret path denied")
    if _is_inside_workspace(path, workspace):
        return RiskDecision(2, "confirm_with_diff", "workspace patch")
    return RiskDecision(6, "deny", "patch outside workspace")


def classify_path(path: str, workspace: str, operation: str) -> RiskDecision:
    target = PureWindowsPath(path)
    if _is_secret_path(target):
        return RiskDecision(6, "deny", "secret path denied")
    if operation == "read" and _is_inside_workspace(path, workspace):
        return RiskDecision(0, "allow", "workspace read")
    if operation == "read":
        return RiskDecision(6, "deny", "path outside workspace")
    if operation == "write" and _is_inside_workspace(path, workspace):
        return RiskDecision(2, "confirm_with_diff", "workspace write")
    return RiskDecision(3, "confirm", "path outside workspace")


def _is_destructive_command(command: str) -> bool:
    if any(command.startswith(pattern) for pattern in DANGEROUS_COMMANDS):
        return True
    return any(fragment.lower() in command for fragment in BLOCKED_COMMAND_FRAGMENTS)


def _is_secret_path(path: PureWindowsPath) -> bool:
    lowered = [part.lower() for part in path.parts]
    return any(name in lowered or name in path.name.lower() for name in SECRET_NAMES)


def _is_inside_workspace(path: str, workspace: str) -> bool:
    target = str(PureWindowsPath(path)).lower()
    root = str(PureWindowsPath(workspace)).lower()
    return target == root or target.startswith(root + "\\")
