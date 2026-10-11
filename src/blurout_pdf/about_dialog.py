"""About dialog shared by both UI languages."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from . import __version__
from .i18n import translate


PROJECT_URL = "https://github.com/janmadrzyk/blur-out-pdf"


class AboutDialog(QDialog):
    def __init__(self, language: str, parent=None) -> None:
        super().__init__(parent)
        t = lambda key, **values: translate(language, key, **values)
        self.setObjectName("aboutDialog")
        self.setWindowTitle(t("about_title"))
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        name = QLabel("BlurOut PDF")
        name.setObjectName("aboutName")
        font = name.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        name.setFont(font)
        layout.addWidget(name)

        version = QLabel(t("about_version", version=__version__))
        version.setObjectName("aboutVersion")
        layout.addWidget(version)
        license_label = QLabel(t("about_license"))
        license_label.setObjectName("aboutLicense")
        layout.addWidget(license_label)

        project = QPushButton(t("about_github"))
        project.setObjectName("aboutProject")
        project.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(PROJECT_URL)))
        layout.addWidget(project)

        close = QPushButton(t("about_close"))
        close.clicked.connect(self.accept)
        layout.addWidget(close)
