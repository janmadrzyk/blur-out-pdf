"""Checks for Windows installer integration at app startup."""

import ctypes
import sys

import pytest

from blurout_pdf.app import INSTALL_MUTEX_NAME, _create_install_mutex


@pytest.mark.skipif(sys.platform != "win32", reason="Windows named mutex")
def test_installer_can_detect_running_app() -> None:
    handle = _create_install_mutex()
    assert handle
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenMutexW.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_wchar_p)
    kernel32.OpenMutexW.restype = ctypes.c_void_p
    second_handle = kernel32.OpenMutexW(0x00100000, False, INSTALL_MUTEX_NAME)
    try:
        assert second_handle
    finally:
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        if second_handle:
            kernel32.CloseHandle(second_handle)
        kernel32.CloseHandle(handle)
