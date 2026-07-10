"""Windows handle-only access to the selected legacy API-key file."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import ntpath
import os
import re
from pathlib import Path

FILE_LIST_DIRECTORY = FILE_READ_DATA = 0x0001
FILE_READ_ATTRIBUTES, DELETE, SYNCHRONIZE = 0x0080, 0x00010000, 0x00100000
FILE_SHARE_ALL, OPEN_EXISTING = 0x00000007, 3
FILE_ATTRIBUTE_DIRECTORY, FILE_ATTRIBUTE_REPARSE_POINT = 0x00000010, 0x00000400
FILE_FLAG_BACKUP_SEMANTICS, FILE_FLAG_OPEN_REPARSE_POINT = 0x02000000, 0x00200000
FILE_OPEN, FILE_DIRECTORY_FILE, FILE_NON_DIRECTORY_FILE = 1, 0x00000001, 0x00000040
FILE_OPEN_REPARSE_POINT, FILE_SYNCHRONOUS_IO_NONALERT, OBJ_CASE_INSENSITIVE = 0x00200000, 0x00000020, 0x00000040
FILE_STANDARD_INFO, FILE_ATTRIBUTE_TAG_INFO, FILE_ID_INFO, FILE_DISPOSITION_INFO = 1, 9, 18, 4
ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND, ERROR_HANDLE_EOF = 2, 3, 38
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class LegacySecretFileError(RuntimeError):
    pass


class _UnicodeString(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", wintypes.LPWSTR)]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [("Length", wintypes.ULONG), ("RootDirectory", wintypes.HANDLE), ("ObjectName", ctypes.POINTER(_UnicodeString)), ("Attributes", wintypes.ULONG), ("SecurityDescriptor", wintypes.LPVOID), ("SecurityQualityOfService", wintypes.LPVOID)]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]


class _AttributeTagInfo(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD)]


class _FileIdInfo(ctypes.Structure):
    _fields_ = [("volume_serial", ctypes.c_ulonglong), ("file_id", ctypes.c_ubyte * 16)]


class _FileStandardInfo(ctypes.Structure):
    _fields_ = [("allocation_size", ctypes.c_longlong), ("end_of_file", ctypes.c_longlong), ("links", wintypes.DWORD), ("delete_pending", wintypes.BOOL), ("directory", wintypes.BOOL)]


class _FileDispositionInfo(ctypes.Structure):
    _fields_ = [("delete_file", ctypes.c_ubyte)]


@dataclass
class LegacySecretFileReference:
    volume_serial: int
    file_id: bytes
    size: int
    _file: wintypes.HANDLE
    _parent: wintypes.HANDLE
    _closed: bool = False


class _WindowsFiles:
    def __init__(self) -> None:
        if os.name != "nt":
            raise LegacySecretFileError("credential_migration_failed")
        self.kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
        self.ntdll = ctypes.WinDLL("Ntdll", use_last_error=True)
        self._configure()

    def _configure(self) -> None:
        self.kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL
        self.kernel32.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        self.kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
        self.kernel32.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
        self.kernel32.ReadFile.restype = wintypes.BOOL
        self.kernel32.SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
        self.kernel32.SetFilePointerEx.restype = wintypes.BOOL
        self.kernel32.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        self.kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
        self.ntdll.NtCreateFile.restype = ctypes.c_long
        self.ntdll.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, ctypes.POINTER(_ObjectAttributes), ctypes.POINTER(_IoStatusBlock), wintypes.LPVOID, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, wintypes.LPVOID, wintypes.ULONG]
        self.ntdll.RtlNtStatusToDosError.argtypes = [ctypes.c_long]
        self.ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG

    def close(self, handle: wintypes.HANDLE) -> None:
        if _valid(handle):
            self.kernel32.CloseHandle(handle)

    def root(self, path: str) -> wintypes.HANDLE:
        handle = self.kernel32.CreateFileW(
            path,
            FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES | SYNCHRONIZE,
            FILE_SHARE_ALL,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
            None,
        )
        if not _valid(handle):
            _raise_winerror()
        return handle

    def child(self, parent: wintypes.HANDLE, name: str, directory: bool, delete: bool = False) -> wintypes.HANDLE:
        buffer = ctypes.create_unicode_buffer(name)
        encoded = name.encode("utf-16-le")
        value = _UnicodeString(len(encoded), len(encoded) + 2, ctypes.cast(buffer, wintypes.LPWSTR))
        attrs = _ObjectAttributes(
            ctypes.sizeof(_ObjectAttributes), parent, ctypes.pointer(value), OBJ_CASE_INSENSITIVE, None, None
        )
        handle = wintypes.HANDLE()
        status = _IoStatusBlock()
        access = FILE_READ_ATTRIBUTES | SYNCHRONIZE | (FILE_LIST_DIRECTORY if directory else FILE_READ_DATA)
        if delete:
            access |= DELETE
        options = FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT
        options |= FILE_DIRECTORY_FILE if directory else FILE_NON_DIRECTORY_FILE
        result = self.ntdll.NtCreateFile(
            ctypes.byref(handle), access, ctypes.byref(attrs), ctypes.byref(status), None, 0,
            FILE_SHARE_ALL, FILE_OPEN, options, None, 0,
        )
        if result < 0:
            raise ctypes.WinError(self.ntdll.RtlNtStatusToDosError(result))
        return handle

    def attributes(self, handle: wintypes.HANDLE) -> _AttributeTagInfo:
        value = _AttributeTagInfo()
        if not self.kernel32.GetFileInformationByHandleEx(handle, FILE_ATTRIBUTE_TAG_INFO, ctypes.byref(value), ctypes.sizeof(value)):
            _raise_winerror()
        return value

    def identity_and_size(self, handle: wintypes.HANDLE) -> tuple[int, bytes, int]:
        identity = _FileIdInfo()
        standard = _FileStandardInfo()
        if not self.kernel32.GetFileInformationByHandleEx(handle, FILE_ID_INFO, ctypes.byref(identity), ctypes.sizeof(identity)):
            _raise_winerror()
        if not self.kernel32.GetFileInformationByHandleEx(handle, FILE_STANDARD_INFO, ctypes.byref(standard), ctypes.sizeof(standard)):
            _raise_winerror()
        return identity.volume_serial, bytes(identity.file_id), standard.end_of_file

    def read(self, handle: wintypes.HANDLE, size: int) -> bytes:
        if not self.kernel32.SetFilePointerEx(handle, 0, None, 0):
            _raise_winerror()
        buffer = (ctypes.c_ubyte * size)()
        read = wintypes.DWORD()
        if not self.kernel32.ReadFile(handle, buffer, size, ctypes.byref(read), None):
            error = ctypes.get_last_error()
            if error != ERROR_HANDLE_EOF:
                raise ctypes.WinError(error)
        return bytes(buffer[:read.value])

    def delete(self, handle: wintypes.HANDLE) -> None:
        info = _FileDispositionInfo(1)
        if not self.kernel32.SetFileInformationByHandle(handle, FILE_DISPOSITION_INFO, ctypes.byref(info), ctypes.sizeof(info)):
            _raise_winerror()


class WindowsLegacySecretFiles:
    """Never follows a reparse point while opening the selected legacy key."""

    def __init__(self) -> None:
        self._native = _WindowsFiles()

    def open_selected(self, selected_workspace: Path) -> LegacySecretFileReference | None:
        workspace = self._open_workspace(selected_workspace)
        bolt = None
        try:
            bolt = self._open_optional(workspace, ".bolt", directory=True)
            if bolt is None:
                return None
            file = self._open_optional(bolt, "desktop-api-key", directory=False, delete=True)
            if file is None:
                return None
            return self._reference(file, bolt)
        except BaseException as error:
            if bolt is not None:
                self._native.close(bolt)
            raise _migration_error(error)
        finally:
            self._native.close(workspace)

    def read_bounded(self, reference: LegacySecretFileReference, limit: int) -> bytes:
        self._assert_reference(reference)
        if limit <= 0:
            raise LegacySecretFileError("credential_migration_failed")
        try:
            content = self._native.read(reference._file, min(reference.size, limit))
            self._assert_reference(reference)
            return content
        except BaseException as error:
            raise _migration_error(error)

    def delete_verified(self, reference: LegacySecretFileReference) -> None:
        self._assert_reference(reference)
        try:
            self._native.delete(reference._file)
            self._native.close(reference._file)
            reference._file = wintypes.HANDLE()
            replacement = self._open_optional(reference._parent, "desktop-api-key", directory=False, delete=False)
            if replacement is not None:
                self._native.close(replacement)
                raise LegacySecretFileError("credential_migration_failed")
        except BaseException as error:
            raise _migration_error(error)
        finally:
            self.close(reference)

    def close(self, reference: LegacySecretFileReference) -> None:
        if reference._closed:
            return
        self._native.close(reference._file)
        self._native.close(reference._parent)
        reference._closed = True

    def _open_workspace(self, selected_workspace: Path) -> wintypes.HANDLE:
        root, components = _workspace_components(selected_workspace)
        current = self._native.root(root)
        try:
            self._assert_directory(current)
            for component in components:
                child = self._native.child(current, component, directory=True)
                self._assert_directory(child)
                self._native.close(current)
                current = child
            return current
        except BaseException:
            self._native.close(current)
            raise

    def _open_optional(self, parent: wintypes.HANDLE, name: str, directory: bool, delete: bool = False):
        try:
            child = self._native.child(parent, name, directory, delete)
        except OSError as error:
            if getattr(error, "winerror", None) in {ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND}:
                return None
            raise
        info = self._native.attributes(child)
        if info.attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            self._native.close(child)
            raise LegacySecretFileError("credential_migration_failed")
        is_directory = bool(info.attributes & FILE_ATTRIBUTE_DIRECTORY)
        if is_directory != directory:
            self._native.close(child)
            raise LegacySecretFileError("credential_migration_failed")
        return child

    def _assert_directory(self, handle: wintypes.HANDLE) -> None:
        info = self._native.attributes(handle)
        if info.attributes & FILE_ATTRIBUTE_REPARSE_POINT or not info.attributes & FILE_ATTRIBUTE_DIRECTORY:
            raise LegacySecretFileError("credential_migration_failed")

    def _reference(self, file: wintypes.HANDLE, parent: wintypes.HANDLE) -> LegacySecretFileReference:
        info = self._native.attributes(file)
        if info.attributes & FILE_ATTRIBUTE_REPARSE_POINT or info.attributes & FILE_ATTRIBUTE_DIRECTORY:
            self._native.close(file)
            raise LegacySecretFileError("credential_migration_failed")
        volume, file_id, size = self._native.identity_and_size(file)
        return LegacySecretFileReference(volume, file_id, size, file, parent)

    def _assert_reference(self, reference: LegacySecretFileReference) -> None:
        if reference._closed or not _valid(reference._file):
            raise LegacySecretFileError("credential_migration_failed")
        current = self._native.identity_and_size(reference._file)
        if current != (reference.volume_serial, reference.file_id, reference.size):
            raise LegacySecretFileError("credential_migration_failed")


def _workspace_components(workspace: Path) -> tuple[str, list[str]]:
    raw = os.fspath(workspace).replace("/", "\\")
    if not ntpath.isabs(raw) or raw.startswith("\\\\"):
        raise LegacySecretFileError("credential_migration_failed")
    drive, tail = ntpath.splitdrive(raw)
    if re.fullmatch(r"[A-Za-z]:", drive) is None or not tail.startswith("\\"):
        raise LegacySecretFileError("credential_migration_failed")
    components = [part for part in tail.split("\\") if part]
    if any(part in {".", ".."} for part in components):
        raise LegacySecretFileError("credential_migration_failed")
    return f"{drive}\\", components


def _valid(handle: wintypes.HANDLE) -> bool:
    value = handle.value if hasattr(handle, "value") else int(handle)
    return value not in {None, 0, INVALID_HANDLE_VALUE}


def _raise_winerror() -> None:
    raise ctypes.WinError(ctypes.get_last_error())


def _migration_error(error: BaseException) -> LegacySecretFileError:
    if isinstance(error, LegacySecretFileError):
        return error
    return LegacySecretFileError("credential_migration_failed")
