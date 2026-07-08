"""Small atomic text-write helper for approved file mutations."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    target = path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        tmp.write_text(content, encoding=encoding)
        os.replace(tmp, target)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
