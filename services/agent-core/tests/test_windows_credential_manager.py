import ctypes

import sys
from uuid import uuid4

import pytest

from bolt_core import windows_credential_manager
from bolt_core.windows_credential_manager import (
    Advapi32CredentialApi,
    CRED_PERSIST_LOCAL_MACHINE,
    CRED_TYPE_GENERIC,
    CredentialStoreError,
    WindowsCredentialManagerStore,
    credential_target,
    new_credential_id,
)


class FakeNative:
    def __init__(self):
        self.values: dict[str, bytes] = {}
        self.freed: list[object] = []

    def write(self, target: str, secret: bytes) -> None:
        self.values[target] = secret

    def read(self, target: str):
        if target not in self.values:
            return None
        return self.values[target], object()

    def delete(self, target: str) -> bool:
        return self.values.pop(target, None) is not None

    def free(self, pointer: object) -> None:
        self.freed.append(pointer)


@pytest.mark.windows
@pytest.mark.skipif(sys.platform != "win32", reason="Windows Credential Manager is required")
def test_real_credential_manager_round_trip_cleans_synthetic_target():
    native = Advapi32CredentialApi()
    store = WindowsCredentialManagerStore(native)
    credential_id = f"wincred.v1.{uuid4()}"
    secret = f"bolt-synthetic-test-{uuid4()}"

    try:
        store.save(credential_id, secret)
        assert store.load(credential_id) == secret
    finally:
        store.delete(credential_id)

    assert store.load(credential_id) is None


def test_advapi_read_frees_native_memory_when_blob_copy_raises(monkeypatch):
    backing = (ctypes.c_ubyte * 1)(65)
    credential = windows_credential_manager._Credential()
    credential.CredentialBlobSize = 1
    credential.CredentialBlob = ctypes.cast(backing, ctypes.POINTER(ctypes.c_ubyte))
    pointer = ctypes.pointer(credential)

    class ReadFunction:
        def __call__(self, _target, _type, _flags, output):
            ctypes.cast(output, ctypes.POINTER(type(pointer)))[0] = pointer
            return True

    class FreeFunction:
        def __init__(self):
            self.calls = []

        def __call__(self, value):
            self.calls.append(value)

    class Library:
        CredReadW = ReadFunction()
        CredFree = FreeFunction()

    api = Advapi32CredentialApi.__new__(Advapi32CredentialApi)
    api._advapi32 = Library()
    monkeypatch.setattr(windows_credential_manager.ctypes, "string_at", lambda *_args: (_ for _ in ()).throw(RuntimeError("copy failed")))

    with pytest.raises(RuntimeError, match="copy failed"):
        api.read("synthetic-target")

    assert len(api._advapi32.CredFree.calls) == 1


def test_advapi_adapter_configures_credential_manager_functions():
    class Function:
        pass

    class Library:
        CredWriteW = Function()
        CredReadW = Function()
        CredDeleteW = Function()
        CredFree = Function()

    api = Advapi32CredentialApi.__new__(Advapi32CredentialApi)
    api._advapi32 = Library()

    api._configure_functions()

    assert api._advapi32.CredWriteW.restype is ctypes.wintypes.BOOL
    assert api._advapi32.CredReadW.restype is ctypes.wintypes.BOOL
    assert api._advapi32.CredDeleteW.restype is ctypes.wintypes.BOOL
    assert api._advapi32.CredFree.restype is None
    assert CRED_TYPE_GENERIC == 1
    assert CRED_PERSIST_LOCAL_MACHINE == 2


def test_generated_id_and_target_are_opaque_and_provider_independent():
    credential_id = new_credential_id()
    target = credential_target(credential_id)

    assert credential_id.startswith("wincred.v1.")
    assert target == f"dev.bolt.desktop/model/v1/{credential_id}"
    for leaked in ("openai", "https", "workspace", "user", "sk-"):
        assert leaked not in target.lower()


def test_round_trip_and_idempotent_delete_use_native_credential_manager():
    native = FakeNative()
    store = WindowsCredentialManagerStore(native)
    credential_id = new_credential_id()

    store.save(credential_id, "synthetic-secret")

    assert store.load(credential_id) == "synthetic-secret"
    assert len(native.freed) == 1
    store.delete(credential_id)
    store.delete(credential_id)
    assert store.load(credential_id) is None


@pytest.mark.parametrize(
    ("secret", "code"),
    [("", "credential_secret_empty"), ("a" * 2561, "credential_secret_too_large")],
)
def test_secret_utf8_byte_boundaries(secret, code):
    store = WindowsCredentialManagerStore(FakeNative())

    with pytest.raises(CredentialStoreError, match=code):
        store.save(new_credential_id(), secret)


def test_accepts_exactly_2560_utf8_bytes():
    native = FakeNative()
    store = WindowsCredentialManagerStore(native)
    credential_id = new_credential_id()

    store.save(credential_id, "é" * 1280)

    assert len(next(iter(native.values.values()))) == 2560


def test_read_always_frees_native_memory_when_utf8_decode_fails():
    native = FakeNative()
    credential_id = new_credential_id()
    pointer = object()
    native.read = lambda _target: (b"\xff", pointer)
    store = WindowsCredentialManagerStore(native)

    with pytest.raises(CredentialStoreError, match="credential_encoding_invalid"):
        store.load(credential_id)

    assert native.freed == [pointer]
