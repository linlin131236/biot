"""Windows AppContainer process launcher for managed Hermes runtimes."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess

from bolt_core.runtime.windows_appcontainer import (
    appcontainer_available, appcontainer_identity, delete_appcontainer_profile,
)
from bolt_core.runtime.windows_job_object import WindowsJobObject
from bolt_core.runtime.workspace_projection import WorkspaceProjectionError

CREATE_NO_WINDOW = 0x08000000
CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
EXTENDED_STARTUPINFO_PRESENT = 0x00080000
STARTF_USESTDHANDLES = 0x00000100
HANDLE_FLAG_INHERIT = 0x00000001
INFINITE = 0xFFFFFFFF
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009


class _StartupInfo(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR), ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.POINTER(ctypes.c_byte)), ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [("startup_info", _StartupInfo), ("attribute_list", wintypes.LPVOID)]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class WindowsManagedProcess:
    def __init__(self, pid, process_handle, stdin, stdout, stderr, job, session_id):
        self.pid = pid
        self._process_handle = process_handle
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self._job = job
        self._session_id = session_id
        self._disposed = False
        self._exit_code = None

    @property
    def job_object_bound(self) -> bool:
        return self._job is not None

    def poll(self):
        if self._exit_code is not None:
            return self._exit_code
        code = wintypes.DWORD()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if not kernel32.GetExitCodeProcess(self._process_handle, ctypes.byref(code)):
            return None
        if code.value == 259:
            return None
        self._exit_code = code.value
        return self._exit_code

    def wait(self, timeout=None):
        milliseconds = INFINITE if timeout is None else int(timeout * 1000)
        result = ctypes.WinDLL("kernel32", use_last_error=True).WaitForSingleObject(
            self._process_handle, milliseconds,
        )
        if result == 0x102:
            raise subprocess.TimeoutExpired(["managed-windows-process"], timeout)
        exit_code = self.poll()
        if exit_code is not None:
            self.dispose()
        return exit_code

    def terminate(self):
        if self._job is not None:
            self._job.close()
            self._job = None
        else:
            self.kill()

    def kill(self):
        ctypes.WinDLL("kernel32", use_last_error=True).TerminateProcess(self._process_handle, 1)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        if self._job is not None:
            self._job.close()
            self._job = None
        for stream in (self.stdin, self.stdout, self.stderr):
            try:
                stream.close()
            except OSError:
                pass
        _close_handle(self._process_handle)
        self._process_handle = wintypes.HANDLE()
        delete_appcontainer_profile(self._session_id)


def restricted_token_available(session_id: str = "session_capability_probe") -> bool:
    return appcontainer_available(session_id)


def start_restricted_process(args, cwd, env, session_id: str) -> WindowsManagedProcess:
    if os.name != "nt" or not restricted_token_available(session_id):
        raise WorkspaceProjectionError("workspace_projection_required")
    pipes = _pipes()
    identity = appcontainer_identity(session_id)
    job = WindowsJobObject.create()
    process_info = None
    try:
        process_info = _create_process(identity, args, cwd, env, pipes)
        try:
            job.assign_process(process_info.hProcess)
            _resume_thread(process_info.hThread)
            _close_child_pipe_fds(pipes)
            return WindowsManagedProcess(
                int(process_info.dwProcessId), process_info.hProcess,
                os.fdopen(pipes["stdin_write_fd"], "wb", buffering=0),
                os.fdopen(pipes["stdout_read_fd"], "rb", buffering=0),
                os.fdopen(pipes["stderr_read_fd"], "rb", buffering=0),
                job,
                session_id,
            )
        finally:
            _close_handle(process_info.hThread)
    except BaseException:
        if process_info is not None:
            ctypes.WinDLL("kernel32", use_last_error=True).TerminateProcess(
                process_info.hProcess, 1,
            )
            _close_handle(process_info.hProcess)
            _close_handle(process_info.hThread)
        job.close()
        _close_pipe_fds(pipes)
        delete_appcontainer_profile(session_id)
        raise
    finally:
        identity.close()


def _create_process(identity, args, cwd, env, pipes):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    command = subprocess.list2cmdline(args)
    environment = _environment_block(env)
    startup, attribute = _startup_info(identity, pipes)
    process_info = _ProcessInformation()
    kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID, wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR, ctypes.POINTER(_StartupInfoEx), ctypes.POINTER(_ProcessInformation)]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    flags = CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT
    try:
        if not kernel32.CreateProcessW(
            os.fspath(args[0]), ctypes.create_unicode_buffer(command), None, None, True, flags,
            environment, os.fspath(cwd), ctypes.byref(startup), ctypes.byref(process_info),
        ):
            raise WorkspaceProjectionError(
                f"workspace_projection_required: create_process_{ctypes.get_last_error()}"
            )
        return process_info
    finally:
        _delete_attribute_list(attribute)


def _startup_info(identity, pipes):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.InitializeProcThreadAttributeList.argtypes = [
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    kernel32.UpdateProcThreadAttribute.argtypes = [
        wintypes.LPVOID, wintypes.DWORD, ctypes.c_size_t, wintypes.LPVOID,
        ctypes.c_size_t, wintypes.LPVOID, ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
    size = ctypes.c_size_t()
    kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
    attribute = ctypes.create_string_buffer(size.value)
    attribute_pointer = ctypes.cast(attribute, wintypes.LPVOID)
    if not kernel32.InitializeProcThreadAttributeList(
        attribute_pointer, 1, 0, ctypes.byref(size),
    ):
        raise WorkspaceProjectionError("workspace_projection_required")
    try:
        caps = identity.capabilities
        if not kernel32.UpdateProcThreadAttribute(
            attribute_pointer, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            ctypes.byref(caps), ctypes.sizeof(caps), None, None,
        ):
            raise WorkspaceProjectionError("workspace_projection_required")
        startup = _StartupInfoEx()
        startup.startup_info.cb = ctypes.sizeof(startup)
        startup.startup_info.dwFlags = STARTF_USESTDHANDLES
        startup.startup_info.hStdInput = pipes["stdin_read"]
        startup.startup_info.hStdOutput = pipes["stdout_write"]
        startup.startup_info.hStdError = pipes["stderr_write"]
        startup.attribute_list = ctypes.cast(attribute, wintypes.LPVOID)
        return startup, attribute
    except BaseException:
        _delete_attribute_list(attribute)
        raise


def _pipes():
    pairs = {}
    for name in ("stdin", "stdout", "stderr"):
        read_fd, write_fd = os.pipe()
        read = msvcrt_handle(read_fd)
        write = msvcrt_handle(write_fd)
        _set_inherit(read, name == "stdin")
        _set_inherit(write, name != "stdin")
        pairs[f"{name}_read_fd"] = read_fd
        pairs[f"{name}_write_fd"] = write_fd
        pairs[f"{name}_read"] = read
        pairs[f"{name}_write"] = write
    return pairs


def msvcrt_handle(fd):
    import msvcrt

    return wintypes.HANDLE(msvcrt.get_osfhandle(fd))


def _set_inherit(handle, inherit):
    ctypes.WinDLL("kernel32", use_last_error=True).SetHandleInformation(
        handle, HANDLE_FLAG_INHERIT, HANDLE_FLAG_INHERIT if inherit else 0,
    )


def _resume_thread(handle):
    if ctypes.WinDLL("kernel32", use_last_error=True).ResumeThread(handle) == 0xFFFFFFFF:
        raise WorkspaceProjectionError("workspace_projection_required")


def _environment_block(env):
    return ctypes.create_unicode_buffer(
        "".join(f"{key}={value}\0" for key, value in sorted(env.items())) + "\0",
    )


def _delete_attribute_list(attribute):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.DeleteProcThreadAttributeList.argtypes = [wintypes.LPVOID]
    kernel32.DeleteProcThreadAttributeList.restype = None
    kernel32.DeleteProcThreadAttributeList(ctypes.cast(attribute, wintypes.LPVOID))


def _close_handle(handle):
    if _valid(handle):
        ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(handle)


def _close_child_pipe_fds(pipes):
    for key in ("stdin_read_fd", "stdout_write_fd", "stderr_write_fd"):
        try:
            os.close(pipes[key])
        except OSError:
            pass


def _close_pipe_fds(pipes):
    for key, value in pipes.items():
        if key.endswith("_fd"):
            try:
                os.close(value)
            except OSError:
                pass


def _valid(handle):
    value = handle.value if hasattr(handle, "value") else int(handle)
    return value not in {None, 0, INVALID_HANDLE_VALUE}
