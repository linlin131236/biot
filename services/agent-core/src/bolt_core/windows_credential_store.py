"""Atomic file-backed storage for DPAPI-protected Bolt credentials."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from bolt_core.windows_dpapi import WindowsDpapiProtector


SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")
_BOLT_ENTROPY = b"Bolt.ModelCredential.v1"


class CredentialProtector(Protocol):
    def protect(self, plaintext: bytes, entropy: bytes) -> bytes: ...

    def unprotect(self, ciphertext: bytes, entropy: bytes) -> bytes: ...


class WindowsCredentialStore:
    def __init__(
        self,
        user_data: str | Path,
        protector: CredentialProtector | None = None,
    ) -> None:
        self._root = Path(user_data).absolute()
        self._directory = self._root / "credentials"
        self._protector = protector or WindowsDpapiProtector()

    def save(self, credential_id: str, secret: str) -> None:
        path = self._path_for(credential_id)
        if not secret:
            raise ValueError("secret is required")
        ciphertext = self._protector.protect(
            secret.encode("utf-8"), self._entropy(credential_id)
        )
        atomic_write_bytes(path, ciphertext)

    def load(self, credential_id: str) -> str | None:
        path = self._path_for(credential_id)
        if not path.exists():
            return None
        plaintext = self._protector.unprotect(
            path.read_bytes(), self._entropy(credential_id)
        )
        return plaintext.decode("utf-8")

    def delete(self, credential_id: str) -> None:
        path = self._path_for(credential_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def exists(self, credential_id: str) -> bool:
        return self._path_for(credential_id).is_file()

    def _path_for(self, credential_id: str) -> Path:
        if SAFE_ID.fullmatch(credential_id) is None:
            raise ValueError("invalid credential id")
        path = self._directory / f"{credential_id}.bin"
        _require_safe_path(self._root, self._directory, path)
        return path

    @staticmethod
    def _entropy(credential_id: str) -> bytes:
        return _BOLT_ENTROPY + b":" + credential_id.encode("ascii")


def _require_safe_path(root: Path, directory: Path, path: Path) -> None:
    if any(_is_link_or_reparse(component) for component in _path_components(root, path)):
        raise ValueError("unsafe credential path")
    if path.absolute().parent != directory:
        raise ValueError("unsafe credential path")


def _path_components(root: Path, path: Path) -> tuple[Path, ...]:
    relative = path.absolute().relative_to(root)
    components = [root]
    current = root
    for part in relative.parts:
        current /= part
        components.append(current)
    return tuple(components)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        _write_synced_exclusive(temporary, content)
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _write_synced_exclusive(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
