"""Payload-local Python support for Windows runtime tests."""

from __future__ import annotations

import atexit
from hashlib import sha256
import os
from pathlib import Path
import shutil
from threading import Lock

REPO_ROOT = Path(__file__).parents[3]
PAYLOAD_ROOT = (
    Path(__file__).parents[1]
    / "src"
    / "bolt_core"
    / "runtime-releases"
    / "hermes"
    / "0.18.2"
)
PAYLOAD_PYTHON = PAYLOAD_ROOT / "bin" / "python.exe"
_TEST_ROOT = REPO_ROOT / ".review-tmp" / f"zcode-hermes-acp-tests-{os.getpid()}"
_INSTALLATION = _TEST_ROOT / "managed" / "hermes" / "0.24.0"
_LOCK = Lock()


def payload_python_sha256() -> str:
    return sha256(PAYLOAD_PYTHON.read_bytes()).hexdigest()


def shared_payload_installation() -> tuple[Path, Path]:
    with _LOCK:
        if not _INSTALLATION.is_dir():
            _INSTALLATION.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(PAYLOAD_ROOT, _INSTALLATION)
    return _TEST_ROOT / "managed", _INSTALLATION


def isolated_payload_installation(name: str) -> tuple[Path, Path]:
    managed = _TEST_ROOT / "isolated" / name
    installation = managed / "hermes" / "0.24.0"
    shutil.copytree(PAYLOAD_ROOT, installation)
    return managed, installation


def cleanup_test_runtime() -> None:
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


atexit.register(cleanup_test_runtime)
