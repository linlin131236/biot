"""Windows ACL enforcement hook for runtime projections."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from bolt_core.runtime.workspace_projection import WorkspaceProjectionError


def enforce_projection_acl(session_root: Path) -> None:
    if os.name != "nt":
        return
    root = Path(session_root)
    if not root.is_dir():
        raise WorkspaceProjectionError("workspace_projection_required")
    _grant_appcontainer(root, "(OI)(CI)F", root.name)


def grant_runtime_read(path: Path, session_id: str) -> None:
    if os.name != "nt":
        return
    target = Path(path)
    if not target.exists():
        raise WorkspaceProjectionError("workspace_projection_required")
    rights = "(OI)(CI)RX" if target.is_dir() else "RX"
    _grant_appcontainer(target, rights, session_id)


def _grant_appcontainer(path: Path, rights: str, session_id: str) -> None:
    from bolt_core.runtime.windows_appcontainer import appcontainer_sid_string

    sid = appcontainer_sid_string(session_id)
    result = subprocess.run(
        ["icacls", os.fspath(path), "/grant", f"*{sid}:{rights}", "/T", "/C"],
        capture_output=True,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        raise WorkspaceProjectionError("workspace_projection_required")
