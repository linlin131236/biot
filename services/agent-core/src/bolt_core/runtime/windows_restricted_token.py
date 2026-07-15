"""Restricted-token capability checks for Windows runtimes."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

from bolt_core.runtime.windows_acl import RESTRICTED_CODE_SID
from bolt_core.runtime.workspace_projection import WorkspaceProjectionError

TOKEN_DUPLICATE = 0x0002
TOKEN_ASSIGN_PRIMARY = 0x0001
TOKEN_QUERY = 0x0008
TOKEN_ADJUST_DEFAULT = 0x0080
TOKEN_ADJUST_SESSIONID = 0x0100
DISABLE_MAX_PRIVILEGE = 0x1
SE_GROUP_ENABLED = 0x00000004
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", wintypes.LPVOID), ("attributes", wintypes.DWORD)]


class RestrictedToken:
    def __init__(self, handle: wintypes.HANDLE) -> None:
        self.handle = handle

    def close(self) -> None:
        if _valid(self.handle):
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(self.handle)
            self.handle = wintypes.HANDLE()


def restricted_token_available() -> bool:
    if os.name != "nt":
        return False
    token = None
    try:
        token = create_restricted_token()
        return True
    except WorkspaceProjectionError:
        return False
    finally:
        if token is not None:
            token.close()


def create_restricted_token() -> RestrictedToken:
    if os.name != "nt":
        raise WorkspaceProjectionError("workspace_projection_required")
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _configure(advapi32)
    access = TOKEN_DUPLICATE | TOKEN_ASSIGN_PRIMARY | TOKEN_QUERY | TOKEN_ADJUST_DEFAULT | TOKEN_ADJUST_SESSIONID
    source = wintypes.HANDLE()
    restricted = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), access, ctypes.byref(source)):
        raise WorkspaceProjectionError(
            f"workspace_projection_required: open_process_token_{ctypes.get_last_error()}"
        )
    restricted_sid = _restricted_sid(advapi32)
    try:
        attributes = (_SidAndAttributes * 1)()
        attributes[0] = _SidAndAttributes(restricted_sid, 0)
        if not advapi32.CreateRestrictedToken(
            source, DISABLE_MAX_PRIVILEGE, 0, None, 0, None, 1,
            attributes, ctypes.byref(restricted),
        ):
            raise WorkspaceProjectionError(
                f"workspace_projection_required: create_restricted_token_{ctypes.get_last_error()}"
            )
        return RestrictedToken(restricted)
    finally:
        advapi32.FreeSid(restricted_sid)
        kernel32.CloseHandle(source)


def _configure(advapi32) -> None:
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.CreateRestrictedToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi32.CreateRestrictedToken.restype = wintypes.BOOL
    advapi32.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPVOID)]
    advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
    advapi32.FreeSid.argtypes = [wintypes.LPVOID]
    advapi32.FreeSid.restype = wintypes.LPVOID


def _restricted_sid(advapi32):
    sid = wintypes.LPVOID()
    if not advapi32.ConvertStringSidToSidW(RESTRICTED_CODE_SID, ctypes.byref(sid)):
        raise WorkspaceProjectionError("workspace_projection_required")
    return sid


def _valid(handle: wintypes.HANDLE) -> bool:
    value = handle.value if hasattr(handle, "value") else int(handle)
    return value not in {None, 0, INVALID_HANDLE_VALUE}
