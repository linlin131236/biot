import json
import os
from pathlib import Path

import pytest

import bolt_core.atomic_write as atomic_write


def test_atomic_write_json_fsyncs_before_same_directory_replace(tmp_path, monkeypatch):
    assert hasattr(atomic_write, "atomic_write_json")
    target = tmp_path / "state.json"
    events: list[str] = []
    real_fsync = os.fsync
    real_replace = os.replace

    def recording_fsync(descriptor: int) -> None:
        events.append("fsync")
        real_fsync(descriptor)

    def recording_replace(source, destination) -> None:
        assert Path(source).parent == target.parent
        assert Path(destination) == target
        events.append("replace")
        real_replace(source, destination)

    monkeypatch.setattr(atomic_write.os, "fsync", recording_fsync)
    monkeypatch.setattr(atomic_write.os, "replace", recording_replace)

    atomic_write.atomic_write_json(target, {"b": 2, "a": 1})

    assert events.index("fsync") < events.index("replace")
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1, "b": 2}


def test_atomic_write_json_cleans_temporary_file_when_replace_fails(tmp_path, monkeypatch):
    assert hasattr(atomic_write, "atomic_write_json")
    target = tmp_path / "state.json"

    def fail_replace(_source, _destination) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(atomic_write.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        atomic_write.atomic_write_json(target, {"state": "pending"})

    assert list(tmp_path.glob(".state.json.*.tmp")) == []
