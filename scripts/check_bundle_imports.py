"""Fail packaging if bundled Qt modules cannot load on Windows."""

import ctypes
import os
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
INTERNAL = PROJECT / "dist" / "BlurOutPDF" / "_internal"


def main() -> None:
    if os.name != "nt":
        raise SystemExit("This check requires Windows")
    directories = (INTERNAL, INTERNAL / "PySide6", INTERNAL / "shiboken6")
    for directory in directories:
        if not directory.is_dir():
            raise SystemExit(f"Missing bundle directory: {directory}")
    handles = [os.add_dll_directory(str(directory)) for directory in directories]
    try:
        for name in ("QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd"):
            path = INTERNAL / "PySide6" / name
            ctypes.WinDLL(str(path))
            print(f"Loaded {name}")
    finally:
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
