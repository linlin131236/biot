import ctypes
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bolt_core import windows_credential_store
from bolt_core.windows_credential_store import WindowsCredentialStore
from bolt_core.windows_dpapi import (
    CredentialProtectionError,
    WindowsDpapiProtector,
    _DataBlob,
    _blob,
)


class FakeProtector:
    def protect(self, plaintext: bytes, entropy: bytes) -> bytes:
        return bytes(value ^ entropy[index % len(entropy)] for index, value in enumerate(plaintext))

    def unprotect(self, ciphertext: bytes, entropy: bytes) -> bytes:
        return self.protect(ciphertext, entropy)


def test_store_round_trips_without_persisting_plaintext(tmp_path):
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    store.save("model.openai", "sk-secret")

    stored = tmp_path / "credentials" / "model.openai.bin"
    assert store.load("model.openai") == "sk-secret"
    assert stored.read_bytes() != b"sk-secret"
    assert b"sk-secret" not in stored.read_bytes()


@pytest.mark.parametrize("credential_id", ["", "../secret", "a/b", "a\\b", "x" * 129])
def test_store_rejects_invalid_credential_ids(tmp_path, credential_id):
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    with pytest.raises(ValueError, match="invalid credential id"):
        store.save(credential_id, "secret")
    with pytest.raises(ValueError, match="invalid credential id"):
        store.load(credential_id)


def test_store_rejects_empty_secret(tmp_path):
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    with pytest.raises(ValueError, match="secret is required"):
        store.save("model.openai", "")


def _make_directory_link(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlink unavailable: {error}")


def _make_junction(link: Path, target: Path) -> None:
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
    )
    if result.returncode:
        pytest.skip(f"junction unavailable (exit {result.returncode})")


def test_store_rejects_credentials_directory_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_directory_link(tmp_path / "credentials", outside)
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    with pytest.raises(ValueError, match="unsafe credential path"):
        store.save("model.openai", "secret")

    assert list(outside.iterdir()) == []


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows junctions are required")
def test_store_rejects_user_data_root_junction_before_creating_credentials(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    user_data = tmp_path / "junction"
    _make_junction(user_data, outside)
    store = WindowsCredentialStore(user_data, FakeProtector())

    with pytest.raises(ValueError, match="unsafe credential path"):
        store.save("model.openai", "secret")

    assert not (outside / "credentials").exists()


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows junctions are required")
def test_store_rejects_credentials_directory_junction(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_junction(tmp_path / "credentials", outside)
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    with pytest.raises(ValueError, match="unsafe credential path"):
        store.save("model.openai", "secret")

    assert list(outside.iterdir()) == []


def test_store_rejects_final_credential_file_symlink(tmp_path):
    directory = tmp_path / "credentials"
    directory.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"unchanged")
    try:
        (directory / "model.openai.bin").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"file symlink unavailable: {error}")
    store = WindowsCredentialStore(tmp_path, FakeProtector())

    for operation in (
        lambda: store.save("model.openai", "secret"),
        lambda: store.load("model.openai"),
        lambda: store.exists("model.openai"),
        lambda: store.delete("model.openai"),
    ):
        with pytest.raises(ValueError, match="unsafe credential path"):
            operation()

    assert outside.read_bytes() == b"unchanged"


def test_save_atomically_replaces_existing_credential(tmp_path, monkeypatch):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    store.save("model.openai", "old-secret")
    replacements = []
    real_replace = os.replace

    def record_replace(source, target):
        replacements.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr("bolt_core.windows_credential_store.os.replace", record_replace)

    store.save("model.openai", "new-secret")

    assert store.load("model.openai") == "new-secret"
    assert len(replacements) == 1
    source, target = replacements[0]
    assert source.parent == target.parent
    assert source != target
    assert target.name == "model.openai.bin"


def test_delete_is_idempotent(tmp_path):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    store.save("model.openai", "secret")

    store.delete("model.openai")
    store.delete("model.openai")

    assert store.exists("model.openai") is False
    assert store.load("model.openai") is None


def test_failed_replace_cleans_temp_and_preserves_old_file(tmp_path, monkeypatch):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    store.save("model.openai", "old-secret")

    def fail_replace(source, target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(windows_credential_store.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        store.save("model.openai", "new-secret")

    assert store.load("model.openai") == "old-secret"
    assert list((tmp_path / "credentials").glob("*.tmp")) == []


def test_atomic_write_exclusively_creates_and_syncs_temp_before_replace(
    tmp_path, monkeypatch
):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    events = []
    real_open = os.open
    real_fsync = os.fsync
    real_replace = os.replace

    def record_open(path, flags, *args, **kwargs):
        events.append(("open", Path(path), flags))
        return real_open(path, flags, *args, **kwargs)

    def record_fsync(fd):
        events.append(("fsync", fd))
        return real_fsync(fd)

    def record_replace(source, target):
        events.append(("replace", Path(source), Path(target)))
        return real_replace(source, target)

    monkeypatch.setattr(windows_credential_store.os, "open", record_open)
    monkeypatch.setattr(windows_credential_store.os, "fsync", record_fsync)
    monkeypatch.setattr(windows_credential_store.os, "replace", record_replace)

    store.save("model.openai", "secret")

    temp_open = next(event for event in events if event[0] == "open")
    assert temp_open[2] & os.O_CREAT
    assert temp_open[2] & os.O_EXCL
    assert next(i for i, event in enumerate(events) if event[0] == "fsync") < next(
        i for i, event in enumerate(events) if event[0] == "replace"
    )


def test_file_sync_failure_cleans_temp_and_preserves_old_file(tmp_path, monkeypatch):
    store = WindowsCredentialStore(tmp_path, FakeProtector())
    store.save("model.openai", "old-secret")

    def fail_fsync(_fd):
        raise OSError("simulated file sync failure")

    monkeypatch.setattr(windows_credential_store.os, "fsync", fail_fsync)

    with pytest.raises(OSError, match="simulated file sync failure"):
        store.save("model.openai", "new-secret")

    assert store.load("model.openai") == "old-secret"
    assert list((tmp_path / "credentials").glob("*.tmp")) == []


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI is required")
def test_real_dpapi_round_trip_uses_only_synthetic_secret():
    protector = WindowsDpapiProtector()
    plaintext = b"bolt-test-synthetic-secret"
    entropy = b"bolt-test-synthetic-entropy"

    ciphertext = protector.protect(plaintext, entropy)

    assert ciphertext != plaintext
    assert protector.unprotect(ciphertext, entropy) == plaintext


def test_blob_keeps_backing_pointer_for_empty_bytes():
    blob, backing = _blob(b"")

    assert blob.cbData == 0
    assert bool(blob.pbData)
    assert backing is not None


def test_dpapi_functions_use_distinct_native_signatures():
    class NativeFunction:
        pass

    class Library:
        CryptProtectData = NativeFunction()
        CryptUnprotectData = NativeFunction()
        LocalFree = NativeFunction()

    protector = WindowsDpapiProtector.__new__(WindowsDpapiProtector)
    protector._crypt32 = Library()
    protector._kernel32 = Library()

    protector._configure_functions()

    protect_description = protector._crypt32.CryptProtectData.argtypes[1]
    unprotect_description = protector._crypt32.CryptUnprotectData.argtypes[1]
    assert protect_description is not unprotect_description
    assert protect_description is ctypes.wintypes.LPCWSTR
    assert unprotect_description is ctypes.POINTER(ctypes.wintypes.LPWSTR)


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI is required")
def test_real_dpapi_round_trips_empty_plaintext():
    protector = WindowsDpapiProtector()
    entropy = b"bolt-test-empty-plaintext"

    ciphertext = protector.protect(b"", entropy)

    assert ciphertext
    assert protector.unprotect(ciphertext, entropy) == b""


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI is required")
@pytest.mark.parametrize("ciphertext", [b"", b"not-a-valid-dpapi-payload"])
def test_real_dpapi_rejects_empty_or_damaged_ciphertext(ciphertext):
    protector = WindowsDpapiProtector()

    with pytest.raises(CredentialProtectionError, match="credential protection failed"):
        protector.unprotect(ciphertext, b"bolt-test-invalid-ciphertext")
