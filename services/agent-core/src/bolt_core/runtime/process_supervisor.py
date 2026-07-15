"""Controlled subprocess lifecycle for external Bolt runtimes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from threading import RLock
from typing import Mapping

from bolt_core.runtime.contracts import is_runtime_id
from bolt_core.runtime.workspace_projection import WorkspaceProjection, WorkspaceProjectionError

_SENSITIVE_ENV_PARTS = ("API_KEY", "AUTHORIZATION", "CREDENTIAL", "TOKEN", "SECRET")
_RUNTIME_ENV_KEYS = frozenset({"BOLT_MODEL_PROXY_URL", "BOLT_RUNTIME_TOKEN", "NO_PROXY"})
_SYSTEM_ENV_KEYS = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")


@dataclass(frozen=True)
class ManagedProcessSpec:
    runtime_id: str
    implementation_version: str
    args: list[str]
    managed_runtime_root: Path
    session_root: Path
    working_directory: Path
    environment: Mapping[str, str]
    workspace_projection: WorkspaceProjection | None = None

    def __post_init__(self) -> None:
        if not is_runtime_id(self.runtime_id):
            raise ValueError("runtime_id must be controlled")
        if not isinstance(self.implementation_version, str) or not self.implementation_version:
            raise ValueError("implementation_version is required")
        self._validate_args()
        self._validate_environment()

    def _validate_args(self) -> None:
        if not isinstance(self.args, list) or not self.args:
            raise ValueError("args must be a non-empty parameter array")
        if any(not isinstance(arg, str) or not arg for arg in self.args):
            raise ValueError("args must contain non-empty strings")

    def _validate_environment(self) -> None:
        if not isinstance(self.environment, Mapping):
            raise ValueError("environment must be a mapping")
        for name, value in self.environment.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise ValueError("environment entries must be strings")
            if name in _RUNTIME_ENV_KEYS:
                continue
            if any(part in name.upper() for part in _SENSITIVE_ENV_PARTS):
                raise ValueError("sensitive environment overrides are forbidden")
            raise ValueError("environment override is not permitted")


@dataclass(frozen=True)
class ManagedProcessRecord:
    pid: int
    runtime_id: str
    implementation_version: str
    args: tuple[str, ...]
    started_at: datetime
    last_heartbeat: datetime
    exit_code: int | None
    job_object_bound: bool = False


class RuntimeProcessSupervisor:
    def __init__(self) -> None:
        self._processes: dict[int, object] = {}
        self._records: dict[int, ManagedProcessRecord] = {}
        self._lock = RLock()

    def start(self, spec: ManagedProcessSpec):
        self._validate_paths(spec)
        environment = self._build_environment(spec)
        process = self._start_process(spec, environment)
        now = datetime.now(UTC)
        record = ManagedProcessRecord(
            pid=process.pid,
            runtime_id=spec.runtime_id,
            implementation_version=spec.implementation_version,
            args=tuple(spec.args),
            started_at=now,
            last_heartbeat=now,
            exit_code=None,
            job_object_bound=bool(getattr(process, "job_object_bound", False)),
        )
        with self._lock:
            self._processes[process.pid] = process
            self._records[process.pid] = record
        return process

    def record(self, pid: int) -> ManagedProcessRecord:
        with self._lock:
            record = self._records[pid]
            process = self._processes[pid]
            return self._refresh_record(record, process)

    def heartbeat(self, pid: int) -> ManagedProcessRecord:
        with self._lock:
            record = self.record(pid)
            updated = ManagedProcessRecord(
                **{**record.__dict__, "last_heartbeat": datetime.now(UTC)}
            )
            self._records[pid] = updated
            return updated

    def stop(self, pid: int, timeout: float) -> ManagedProcessRecord:
        if not isinstance(timeout, (int, float)) or timeout < 0:
            raise ValueError("timeout must be non-negative")
        with self._lock:
            process = self._processes[pid]
        if process.poll() is None:
            self._terminate(process, timeout)
        return self.record(pid)

    def stop_all(self, timeout: float) -> tuple[ManagedProcessRecord, ...]:
        if not isinstance(timeout, (int, float)) or timeout < 0:
            raise ValueError("timeout must be non-negative")
        with self._lock:
            pids = tuple(self._processes)
        records = []
        for pid in pids:
            try:
                records.append(self.stop(pid, timeout))
            except KeyError:
                continue
        return tuple(records)

    def _start_process(self, spec: ManagedProcessSpec, environment: dict[str, str]):
        if self._requires_windows_projection(spec):
            from bolt_core.runtime.windows_acl import grant_runtime_read
            from bolt_core.runtime.windows_process import start_restricted_process

            grant_runtime_read(Path(spec.args[0]).parent.parent, spec.session_root.name)
            return start_restricted_process(
                spec.args, spec.working_directory, environment, spec.session_root.name,
            )
        return subprocess.Popen(
            spec.args,
            cwd=spec.working_directory,
            env=environment,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _terminate(self, process, timeout: float) -> None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _validate_paths(self, spec: ManagedProcessSpec) -> None:
        root = spec.managed_runtime_root.resolve()
        session = spec.session_root.resolve()
        working_directory = spec.working_directory.resolve()
        if not self._is_within(session, root):
            raise ValueError("session_root must be inside managed_runtime_root")
        if self._requires_projection(spec):
            self._validate_projection(spec, working_directory)
        elif not self._is_within(working_directory, session):
            raise ValueError("working_directory must be inside session_root")
        for directory in (root, session, working_directory):
            directory.mkdir(parents=True, exist_ok=True)

    def _validate_projection(self, spec: ManagedProcessSpec, working_directory: Path) -> None:
        projection = spec.workspace_projection
        if projection is None or not projection.acl_enforced:
            raise WorkspaceProjectionError("workspace_projection_required")
        if projection.session_root.resolve() != spec.session_root.resolve():
            raise WorkspaceProjectionError("workspace_projection_required")
        projection.validate_runtime_cwd(working_directory)

    def _build_environment(self, spec: ManagedProcessSpec) -> dict[str, str]:
        environment = {name: os.environ[name] for name in _SYSTEM_ENV_KEYS if name in os.environ}
        system_root = environment.get("SYSTEMROOT") or environment.get("WINDIR")
        if system_root:
            environment["PATH"] = str(Path(system_root) / "System32")
        environment.update(spec.environment)
        roots = self._runtime_directories(spec)
        environment.update({name: str(path) for name, path in roots.items()})
        if spec.workspace_projection is not None:
            home = spec.workspace_projection.home
            appdata = home / "AppData" / "Roaming"
            local_appdata = home / "AppData" / "Local"
            appdata.mkdir(parents=True, exist_ok=True)
            local_appdata.mkdir(parents=True, exist_ok=True)
            environment.update({
                "USERPROFILE": str(home),
                "APPDATA": str(appdata),
                "LOCALAPPDATA": str(local_appdata),
                "HOMEDRIVE": home.drive,
                "HOMEPATH": str(home)[len(home.drive):] if home.drive else str(home),
            })
        for directory in set(roots.values()):
            directory.mkdir(parents=True, exist_ok=True)
        return environment

    def _runtime_directories(self, spec: ManagedProcessSpec) -> dict[str, Path]:
        if spec.workspace_projection is not None:
            projection = spec.workspace_projection
            return {
                "HERMES_HOME": projection.hermes_home,
                "HOME": projection.home,
                "TEMP": projection.temp,
                "TMP": projection.temp,
            }
        return {
            "HERMES_HOME": spec.session_root / "hermes-home",
            "HOME": spec.session_root / "home",
            "TEMP": spec.session_root / "temp",
            "TMP": spec.session_root / "temp",
        }

    def _refresh_record(self, record: ManagedProcessRecord, process) -> ManagedProcessRecord:
        exit_code = process.poll()
        if exit_code == record.exit_code:
            return record
        updated = ManagedProcessRecord(**{**record.__dict__, "exit_code": exit_code})
        self._records[record.pid] = updated
        if exit_code is not None:
            disposer = getattr(process, "dispose", None)
            if callable(disposer):
                disposer()
        return updated

    @staticmethod
    def _requires_projection(spec: ManagedProcessSpec) -> bool:
        return os.name == "nt" and spec.runtime_id == "hermes"

    @staticmethod
    def _requires_windows_projection(spec: ManagedProcessSpec) -> bool:
        return os.name == "nt" and spec.runtime_id == "hermes"

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True
