"""Small atomic text-write helper for approved file mutations."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding=encoding, newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def atomic_write_json(path: Path, value: object) -> None:
    content = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    atomic_write_text(path, content)
