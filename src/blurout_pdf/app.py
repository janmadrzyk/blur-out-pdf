"""Application entry point."""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("BlurOut PDF")
    app.setOrganizationName("BlurOut PDF")
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "app.png")))
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
