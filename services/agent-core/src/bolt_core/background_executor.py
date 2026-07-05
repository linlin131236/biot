"""Background process management: spawn, poll, kill.

Uses a background thread per process to continuously consume stdout,
preventing pipe buffer deadlock. Completed process refs are released
after final output collection.
"""

import subprocess
import threading
import uuid
from dataclasses import dataclass

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
    """Manages background processes: spawn, poll, kill."""

    def __init__(self, workspace: str,
                 max_output_size: int = _DEFAULT_MAX_OUTPUT) -> None:
        self.workspace = workspace
        self._processes: dict[str, subprocess.Popen] = {}
        self._output: dict[str, str] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._max_output_size = max_output_size

    def spawn(self, command: str, workdir: str | None = None) -> BackgroundProcess:
        effective_workdir = workdir or self.workspace
        check = PathGuard(self.workspace).check(effective_workdir)
        if not check.allowed:
            return BackgroundProcess("", command, effective_workdir, "failed", check.reason)
        if not check.path.is_dir():
            return BackgroundProcess("", command, effective_workdir, "failed", "workdir is not a directory")
        session_id = f"bg_{uuid.uuid4().hex[:12]}"
        try:
            proc = subprocess.Popen(
                command, cwd=str(check.path), shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
        except OSError as exc:
            return BackgroundProcess(session_id, command, effective_workdir, "failed", str(exc))
        self._processes[session_id] = proc
        self._output[session_id] = ""
        # Background thread consumes stdout to prevent pipe deadlock
        t = threading.Thread(target=self._reader, args=(session_id, proc), daemon=True)
        self._threads[session_id] = t
        t.start()
        return BackgroundProcess(session_id, command, effective_workdir, "running", "")

    def poll(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        retcode = proc.poll()
        if retcode is None:
            return BackgroundProcess(session_id, proc.args, "", "running", self._output.get(session_id, ""))
        # Process finished — release ref
        self._threads.pop(session_id, None)
        self._processes.pop(session_id, None)
        status = "completed" if retcode == 0 else "failed"
        return BackgroundProcess(session_id, proc.args, "", status, self._output.pop(session_id, ""))

    def kill(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        self._threads.pop(session_id, None)
        self._processes.pop(session_id, None)
        return BackgroundProcess(session_id, proc.args, "", "killed", self._output.pop(session_id, ""))

    def list_sessions(self) -> list[BackgroundProcess]:
        return [self.poll(sid) for sid in list(self._processes.keys())]

    def full_output(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        retcode = proc.poll()
        status = "running" if retcode is None else ("completed" if retcode == 0 else "failed")
        return BackgroundProcess(session_id, proc.args, "", status, self._output.get(session_id, ""))

    def _reader(self, session_id: str, proc: subprocess.Popen) -> None:
        """Background thread: continuously reads stdout."""
        try:
            for line in proc.stdout:
                current = self._output.get(session_id, "")
                if len(current) < self._max_output_size:
                    appended = current + line
                    if len(appended) > self._max_output_size:
                        appended = appended[:self._max_output_size] + "\n[output truncated]"
                    self._output[session_id] = appended
        except Exception:
            pass
