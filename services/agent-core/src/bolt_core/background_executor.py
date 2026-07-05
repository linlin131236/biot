"""Background process management: spawn, poll, kill."""

import subprocess
import uuid
from dataclasses import dataclass

from bolt_core.path_guard import PathGuard


@dataclass(frozen=True)
class BackgroundProcess:
    session_id: str
    command: str
    workdir: str
    status: str
    output: str


class BackgroundExecutor:
    """Manages background processes: spawn, poll, kill."""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace
        self._processes: dict[str, subprocess.Popen] = {}
        self._output: dict[str, str] = {}

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
                command,
                cwd=str(check.path),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as exc:
            return BackgroundProcess(session_id, command, effective_workdir, "failed", str(exc))
        self._processes[session_id] = proc
        self._output[session_id] = ""
        return BackgroundProcess(session_id, command, effective_workdir, "running", "")

    def poll(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        self._collect_output(session_id, proc)
        retcode = proc.poll()
        if retcode is None:
            return BackgroundProcess(session_id, proc.args, "", "running", self._output.get(session_id, ""))
        status = "completed" if retcode == 0 else "failed"
        return BackgroundProcess(session_id, proc.args, "", status, self._output.get(session_id, ""))

    def kill(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        self._collect_output(session_id, proc)
        self._processes.pop(session_id, None)
        return BackgroundProcess(session_id, proc.args, "", "killed", self._output.get(session_id, ""))

    def list_sessions(self) -> list[BackgroundProcess]:
        result = []
        for session_id in list(self._processes.keys()):
            result.append(self.poll(session_id))
        return result

    def full_output(self, session_id: str) -> BackgroundProcess:
        proc = self._processes.get(session_id)
        if proc is None:
            return BackgroundProcess(session_id, "", "", "unknown", "session not found")
        self._collect_output(session_id, proc)
        retcode = proc.poll()
        status = "running" if retcode is None else ("completed" if retcode == 0 else "failed")
        return BackgroundProcess(session_id, proc.args, "", status, self._output.get(session_id, ""))

    def _collect_output(self, session_id: str, proc: subprocess.Popen) -> None:
        try:
            import io
            buf = io.StringIO()
            while True:
                chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, 'read1') else ""
                if not chunk:
                    break
                buf.write(chunk)
            new_output = buf.getvalue()
        except Exception:
            new_output = ""
        if new_output:
            self._output[session_id] = self._output.get(session_id, "") + new_output
