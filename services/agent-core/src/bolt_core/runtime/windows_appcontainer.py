"""Windows AppContainer identity for managed external runtimes."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

from bolt_core.runtime.workspace_projection import WorkspaceProjectionError

APP_CONTAINER_PREFIX = "Bolt.HermesRuntime"
ERROR_ALREADY_EXISTS_HRESULT = ctypes.c_long(0x800700B7).value


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("sid", wintypes.LPVOID), ("attributes", wintypes.DWORD)]


class SecurityCapabilities(ctypes.Structure):
    _fields_ = [
        ("app_container_sid", wintypes.LPVOID),
        ("capabilities", ctypes.POINTER(_SidAndAttributes)),
        ("capability_count", wintypes.DWORD),
        ("reserved", wintypes.DWORD),
    ]


class AppContainerIdentity:
    def __init__(self, sid: wintypes.LPVOID) -> None:
        self.sid = sid
        self.capabilities = SecurityCapabilities(sid, None, 0, 0)

    def close(self) -> None:
        if self.sid:
            ctypes.WinDLL("advapi32", use_last_error=True).FreeSid(self.sid)
            self.sid = wintypes.LPVOID()


def appcontainer_available(session_id: str = "session_capability_probe") -> bool:
    if os.name != "nt":
        return False
    identity = None
    try:
        identity = appcontainer_identity(session_id)
        return True
    except WorkspaceProjectionError:
        return False
    finally:
        if identity is not None:
            identity.close()


def appcontainer_identity(session_id: str) -> AppContainerIdentity:
    if os.name != "nt" or not _valid_session_id(session_id):
        raise WorkspaceProjectionError("workspace_projection_required")
    sid = _create_or_derive_sid(_profile_name(session_id))
    return AppContainerIdentity(sid)


def appcontainer_sid_string(session_id: str) -> str:
    if os.name != "nt" or not _valid_session_id(session_id):
        raise WorkspaceProjectionError("workspace_projection_required")
    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    identity = AppContainerIdentity(_derive_sid(userenv, _profile_name(session_id)))
    try:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32.ConvertSidToStringSidW.argtypes = [
            wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR),
        ]
        advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
        value = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(identity.sid, ctypes.byref(value)):
            raise WorkspaceProjectionError("workspace_projection_required")
        try:
            return value.value
        finally:
            kernel32.LocalFree(value)
    finally:
        identity.close()


def delete_appcontainer_profile(session_id: str) -> None:
    if os.name != "nt" or not _valid_session_id(session_id):
        return
    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
    userenv.DeleteAppContainerProfile.restype = ctypes.c_long
    userenv.DeleteAppContainerProfile(_profile_name(session_id))


def _profile_name(session_id: str) -> str:
    return f"{APP_CONTAINER_PREFIX}.{session_id}"


def _valid_session_id(value: object) -> bool:
    return isinstance(value, str) and value.startswith("session_") and value.replace("_", "").isalnum()


def _create_or_derive_sid(profile_name: str):
    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    userenv.CreateAppContainerProfile.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
        ctypes.POINTER(_SidAndAttributes), wintypes.DWORD,
        ctypes.POINTER(wintypes.LPVOID),
    ]
    userenv.CreateAppContainerProfile.restype = ctypes.c_long
    sid = wintypes.LPVOID()
    result = userenv.CreateAppContainerProfile(
        profile_name, profile_name, "Bolt managed Hermes runtime",
        None, 0, ctypes.byref(sid),
    )
    if result == 0 and sid:
        return sid
    if result != ERROR_ALREADY_EXISTS_HRESULT:
        raise WorkspaceProjectionError(
            f"workspace_projection_required: create_appcontainer_profile_{result}"
        )
    return _derive_sid(userenv, profile_name)


def _derive_sid(userenv, profile_name: str):
    userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
        wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPVOID),
    ]
    userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
    sid = wintypes.LPVOID()
    result = userenv.DeriveAppContainerSidFromAppContainerName(
        profile_name, ctypes.byref(sid),
    )
    if result < 0 or not sid:
        raise WorkspaceProjectionError("workspace_projection_required")
    return sid
