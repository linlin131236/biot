from dataclasses import dataclass

from bolt_core.path_guard import PathGuard

MAX_READ_BYTES = 256 * 1024


@dataclass(frozen=True)
class FileReadOutcome:
    status: str
    path: str
    content: str | None
    error: str | None


def read_workspace_file(path: str, workspace: str) -> FileReadOutcome:
    check = PathGuard(workspace).check(path)
    if not check.allowed:
        return FileReadOutcome("failed", path, None, check.reason)
    data = _read_bytes(check.path)
    if isinstance(data, FileReadOutcome):
        return data
    text = _decode_text(check.path, data)
    if isinstance(text, FileReadOutcome):
        return text
    return FileReadOutcome("executed", str(check.path), text, None)


def _read_bytes(path) -> FileReadOutcome | bytes:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return FileReadOutcome("failed", str(path), None, "file not found")
    except OSError as exc:
        return FileReadOutcome("failed", str(path), None, f"read error: {exc}")
    if len(data) > MAX_READ_BYTES:
        return FileReadOutcome("failed", str(path), None, "file exceeds read limit")
    return data


def _decode_text(path, data: bytes) -> FileReadOutcome | str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return FileReadOutcome("failed", str(path), None, "binary file not readable")
