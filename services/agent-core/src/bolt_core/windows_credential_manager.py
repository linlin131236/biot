from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import re
from typing import Protocol
from uuid import uuid4


_ID = re.compile(r"^wincred\.v1\.[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


class Advapi32CredentialApi:
    def __init__(self) -> None:
        self._advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
        self._configure_functions()

    def _configure_functions(self) -> None:
        credential_pointer = ctypes.POINTER(_Credential)
        self._advapi32.CredWriteW.argtypes = [credential_pointer, wintypes.DWORD]
        self._advapi32.CredWriteW.restype = wintypes.BOOL
        self._advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(credential_pointer)]
        self._advapi32.CredReadW.restype = wintypes.BOOL
        self._advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._advapi32.CredDeleteW.restype = wintypes.BOOL
        self._advapi32.CredFree.argtypes = [ctypes.c_void_p]
        self._advapi32.CredFree.restype = None

    def write(self, target: str, secret: bytes) -> None:
        backing = (ctypes.c_ubyte * len(secret)).from_buffer_copy(secret)
        credential = _Credential()
        credential.Type = CRED_TYPE_GENERIC
        credential.TargetName = target
        credential.CredentialBlobSize = len(secret)
        credential.CredentialBlob = ctypes.cast(backing, ctypes.POINTER(ctypes.c_ubyte))
        credential.Persist = CRED_PERSIST_LOCAL_MACHINE
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise ctypes.WinError(ctypes.get_last_error())

    def read(self, target: str) -> tuple[bytes, object] | None:
        pointer = ctypes.POINTER(_Credential)()
        if not self._advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            error = ctypes.get_last_error()
            if error == ERROR_NOT_FOUND:
                return None
            raise ctypes.WinError(error)
        try:
            credential = pointer.contents
            content = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        except BaseException:
            self._advapi32.CredFree(ctypes.cast(pointer, ctypes.c_void_p))
            raise
        return content, pointer

    def delete(self, target: str) -> bool:
        if self._advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0):
            return True
        error = ctypes.get_last_error()
        if error == ERROR_NOT_FOUND:
            return False
        raise ctypes.WinError(error)

    def free(self, pointer: object) -> None:
        self._advapi32.CredFree(ctypes.cast(pointer, ctypes.c_void_p))


class CredentialStoreError(RuntimeError):
    pass


class CredentialNativeApi(Protocol):
    def write(self, target: str, secret: bytes) -> None: ...
    def read(self, target: str) -> tuple[bytes, object] | None: ...
    def delete(self, target: str) -> bool: ...
    def free(self, pointer: object) -> None: ...


def new_credential_id() -> str:
    return f"wincred.v1.{uuid4()}"


def credential_target(credential_id: str) -> str:
    if _ID.fullmatch(credential_id) is None:
        raise CredentialStoreError("credential_invalid_id")
    return f"dev.bolt.desktop/model/v1/{credential_id}"


@dataclass
class WindowsCredentialManagerStore:
    native: CredentialNativeApi

    def save(self, credential_id: str, secret: str) -> None:
        target = credential_target(credential_id)
        encoded = secret.encode("utf-8")
        if not encoded:
            raise CredentialStoreError("credential_secret_empty")
        if len(encoded) > 2560:
            raise CredentialStoreError("credential_secret_too_large")
        try:
            self.native.write(target, encoded)
        except OSError as error:
            raise CredentialStoreError("credential_write_failed") from error

    def load(self, credential_id: str) -> str | None:
        target = credential_target(credential_id)
        try:
            result = self.native.read(target)
        except OSError as error:
            raise CredentialStoreError("credential_read_failed") from error
        if result is None:
            return None
        content, pointer = result
        try:
            return content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise CredentialStoreError("credential_encoding_invalid") from error
        finally:
            self.native.free(pointer)

    def delete(self, credential_id: str) -> None:
        target = credential_target(credential_id)
        try:
            self.native.delete(target)
        except OSError as error:
            raise CredentialStoreError("credential_delete_failed") from error

    def exists(self, credential_id: str) -> bool:
        return self.load(credential_id) is not None
