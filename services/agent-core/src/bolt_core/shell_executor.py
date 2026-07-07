import subprocess
from dataclasses import dataclass

from bolt_core.command_security import parse_command_argv
from bolt_core.path_guard import PathGuard
from bolt_core.tool_protocol import ToolRequest

DEFAULT_TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 100 * 1024


@dataclass(frozen=True)
class ShellExecutionOutcome:
    status: str
    output: str | None
    error: str | None


def execute_shell_command(request: ToolRequest, workspace: str) -> ShellExecutionOutcome:
    command = str(request.payload.get("command", "")).strip()
    workdir = str(request.payload.get("workdir", workspace))
    timeout = _timeout(request.payload.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
    check = PathGuard(workspace).check(workdir)
    if not check.allowed:
        return ShellExecutionOutcome("failed", None, check.reason)
    if not check.path.is_dir():
        return ShellExecutionOutcome("failed", None, "workdir is not a directory")
    if not command:
        return ShellExecutionOutcome("failed", None, "empty command")
    return _run(command, str(check.path), timeout)


def _run(command: str, workdir: str, timeout: int) -> ShellExecutionOutcome:
    parsed, error = parse_command_argv(command)
    if error is not None or parsed is None:
        return ShellExecutionOutcome("failed", None, error or "invalid command")
    try:
        result = subprocess.run(parsed.argv, cwd=workdir, shell=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ShellExecutionOutcome("failed", None, "command timed out")
    except OSError as exc:
        return ShellExecutionOutcome("failed", None, f"command failed to start: {exc}")
    output = _limit_output((result.stdout or "") + (result.stderr or ""))
    if result.returncode != 0:
        return ShellExecutionOutcome("failed", output, f"command exited with {result.returncode}")
    return ShellExecutionOutcome("executed", output, None)


def _limit_output(output: str) -> str:
    data = output.encode("utf-8")
    if len(data) <= MAX_OUTPUT_BYTES:
        return output
    clipped = data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return clipped + "\n[output truncated]"


def _timeout(value) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS
    return max(1, min(parsed, DEFAULT_TIMEOUT_SECONDS))
