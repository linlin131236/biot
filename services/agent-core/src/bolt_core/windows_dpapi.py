"""Current-user Windows DPAPI protection for Bolt credentials."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class CredentialProtectionError(RuntimeError):
    """Raised when credential protection cannot be completed."""


_ERROR_MESSAGE = "credential protection failed"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
    return _DataBlob(len(data), pointer), buffer


class WindowsDpapiProtector:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise CredentialProtectionError("Windows DPAPI is unavailable")
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_functions()

    def protect(self, plaintext: bytes, entropy: bytes) -> bytes:
        return self._transform("CryptProtectData", plaintext, entropy)

    def unprotect(self, ciphertext: bytes, entropy: bytes) -> bytes:
        return self._transform("CryptUnprotectData", ciphertext, entropy)

    def _configure_functions(self) -> None:
        tail = [
            ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, *tail,
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR), *tail,
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        self._kernel32.LocalFree.restype = wintypes.HLOCAL

    def _transform(self, name: str, data: bytes, entropy: bytes) -> bytes:
        input_blob, input_buffer = _blob(data)
        entropy_blob, entropy_buffer = _blob(entropy)
        output_blob = _DataBlob()
        function = getattr(self._crypt32, name)
        try:
            if not function(
                ctypes.byref(input_blob), None, ctypes.byref(entropy_blob), None,
                None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(output_blob),
            ):
                raise CredentialProtectionError(_ERROR_MESSAGE)
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        except CredentialProtectionError:
            raise
        except Exception as error:
            raise CredentialProtectionError(_ERROR_MESSAGE) from error
        finally:
            _ = input_buffer, entropy_buffer
            if output_blob.pbData:
                self._kernel32.LocalFree(ctypes.cast(output_blob.pbData, wintypes.HLOCAL))
