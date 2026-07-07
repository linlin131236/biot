"""Background process management: spawn, poll, kill."""

import subprocess
import threading
import uuid
from dataclasses import dataclass

from bolt_core.command_security import parse_command_argv
from bolt_core.path_guard import PathGuard

_DEFAULT_MAX_OUTPUT = 1_048_576  # 1MB


@dataclass(frozen=True)
class BackgroundProcess:
    session_id: str
    command: str
    workdir: str
    status: str
    output: str


class BackgroundExecutor:
    """Manages background processes without invoking a shell."""

    def __init__(self, workspace: str,
                 max_output_size: int = _DEFAULT_MAX_OUTPUT) -> None:
        self.workspace = workspace
        self._processes: dict[str, subprocess.Popen] = {}
        self._output: dict[str, str] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._max_output_size = max_output_size

    def spawn(self, command: str, workdir: str | None = None) -> BackgroundProcess:
        effective_workdir = workdir or self.workspace
        check = PathGuard(self.workspace).check(effective_workdir)
        if not check.allowed:
            return BackgroundProcess("", command, effective_workdir, "failed", check.reason)
        if not check.path.is_dir():
            return BackgroundProcess("", command, effective_workdir, "failed", "workdir is not a directory")
        parsed, error = parse_command_argv(command)
        if error is not None or parsed is None:
            return BackgroundProcess("", command, effective_workdir, "failed", error or "invalid command")
        session_id = f"bg_{uuid.uuid4().hex[:12]}"
        try:
            proc = subprocess.Popen(
                parsed.argv, cwd=str(check.path), shell=False,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        except OSError as exc:
            return BackgroundProcess(session_id, command, effective_workdir, "failed", str(exc))
        with self._lock:
            self._processes[session_id] = proc
            self._output[session_id] = ""
        thread = threading.Thread(target=self._reader, args=(session_id, proc), daemon=True)
        with self._lock:
            self._threads[session_id] = thread
        thread.start()
        return BackgroundProcess(session_id, command, effective_workdir, "running", "")

    def poll(self, session_id: str) -> BackgroundProcess:
        with self._lock:
            proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        retcode = proc.poll()
        if retcode is None:
            with self._lock:
                output = self._output.get(session_id, "")
            return BackgroundProcess(session_id, _display_args(proc.args), "", "running", output)
        with self._lock:
            self._threads.pop(session_id, None)
            self._processes.pop(session_id, None)
            output = self._output.pop(session_id, "")
        status = "completed" if retcode == 0 else "failed"
        return BackgroundProcess(session_id, _display_args(proc.args), "", status, output)

    def kill(self, session_id: str) -> BackgroundProcess:
        with self._lock:
            proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        with self._lock:
            self._threads.pop(session_id, None)
            self._processes.pop(session_id, None)
            output = self._output.pop(session_id, "")
        return BackgroundProcess(session_id, _display_args(proc.args), "", "killed", output)

    def list_sessions(self) -> list[BackgroundProcess]:
        with self._lock:
            session_ids = list(self._processes.keys())
        return [self.poll(sid) for sid in session_ids]

    def full_output(self, session_id: str) -> BackgroundProcess:
        with self._lock:
            proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        retcode = proc.poll()
        status = "running" if retcode is None else ("completed" if retcode == 0 else "failed")
        with self._lock:
            output = self._output.get(session_id, "")
        return BackgroundProcess(session_id, _display_args(proc.args), "", status, output)

    def _reader(self, session_id: str, proc: subprocess.Popen) -> None:
        try:
            if proc.stdout is None:
                return
            for line in proc.stdout:
                with self._lock:
                    current = self._output.get(session_id, "")
                if len(current) < self._max_output_size:
                    appended = current + line
                    if len(appended) > self._max_output_size:
                        appended = appended[:self._max_output_size] + "\n[output truncated]"
                    with self._lock:
                        self._output[session_id] = appended
        except Exception:
            pass


def _display_args(args) -> str:
    if isinstance(args, list):
        return " ".join(str(arg) for arg in args)
    return str(args)
