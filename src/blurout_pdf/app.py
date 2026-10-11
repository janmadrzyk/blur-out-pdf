"""Application entry point."""

import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from . import __version__
from .window import MainWindow


INSTALL_MUTEX_NAME = "Local\\BlurOutPDF.PDF.Reader"


def _create_install_mutex():
    if sys.platform != "win32":
        return None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel32.CreateMutexW(None, False, INSTALL_MUTEX_NAME)
    if not mutex:
        raise OSError(ctypes.get_last_error(), "Could not create application mutex")
    return mutex


def main() -> int:
    mutex = _create_install_mutex()
    app = QApplication(sys.argv)
    app.setApplicationName("BlurOut PDF")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BlurOut PDF")
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "app.png")))
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    try:
        return app.exec()
    finally:
        if mutex:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
            kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    raise SystemExit(main())
