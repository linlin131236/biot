"""Windows Job Object wrapper for managed runtime process trees."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os

from bolt_core.runtime.workspace_projection import WorkspaceProjectionError

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JobObjectExtendedLimitInformation = 9
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _IoCounters(ctypes.Structure):
    _fields_ = [("read_operation_count", ctypes.c_ulonglong), ("write_operation_count", ctypes.c_ulonglong), ("other_operation_count", ctypes.c_ulonglong), ("read_transfer_count", ctypes.c_ulonglong), ("write_transfer_count", ctypes.c_ulonglong), ("other_transfer_count", ctypes.c_ulonglong)]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [("per_process_user_time_limit", ctypes.c_longlong), ("per_job_user_time_limit", ctypes.c_longlong), ("limit_flags", wintypes.DWORD), ("minimum_working_set_size", ctypes.c_size_t), ("maximum_working_set_size", ctypes.c_size_t), ("active_process_limit", wintypes.DWORD), ("affinity", ctypes.c_size_t), ("priority_class", wintypes.DWORD), ("scheduling_class", wintypes.DWORD)]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [("basic_limit_information", _BasicLimitInformation), ("io_info", _IoCounters), ("process_memory_limit", ctypes.c_size_t), ("job_memory_limit", ctypes.c_size_t), ("peak_process_memory_used", ctypes.c_size_t), ("peak_job_memory_used", ctypes.c_size_t)]


class WindowsJobObject:
    def __init__(self, handle: wintypes.HANDLE) -> None:
        self.handle = handle

    @classmethod
    def create(cls) -> "WindowsJobObject":
        if os.name != "nt":
            raise WorkspaceProjectionError("workspace_projection_required")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        handle = kernel32.CreateJobObjectW(None, None)
        if not _valid(handle):
            raise WorkspaceProjectionError("workspace_projection_required")
        job = cls(handle)
        try:
            job._enable_kill_on_close()
            return job
        except BaseException:
            job.close()
            raise

    def assign_process(self, process_handle: wintypes.HANDLE) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        if not kernel32.AssignProcessToJobObject(self.handle, process_handle):
            raise WorkspaceProjectionError("workspace_projection_required")

    def close(self) -> None:
        if _valid(self.handle):
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(self.handle)
            self.handle = wintypes.HANDLE()

    def _enable_kill_on_close(self) -> None:
        info = _ExtendedLimitInformation()
        info.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        if not kernel32.SetInformationJobObject(
            self.handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info),
        ):
            raise WorkspaceProjectionError("workspace_projection_required")


def _valid(handle: wintypes.HANDLE) -> bool:
    value = handle.value if hasattr(handle, "value") else int(handle)
    return value not in {None, 0, INVALID_HANDLE_VALUE}
