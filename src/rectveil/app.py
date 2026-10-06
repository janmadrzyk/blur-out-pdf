"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from .window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Rectveil")
    app.setOrganizationName("Rectveil")
    window = MainWindow(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
