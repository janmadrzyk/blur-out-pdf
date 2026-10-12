"""Capture the current UI using a synthetic PDF and project-local settings."""

from pathlib import Path
import sys
from unittest.mock import patch

import pymupdf
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QStyleFactory

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from blurout_pdf import __version__, search, window as window_module


def create_sample(sample: Path) -> None:
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=595, height=842)
        page.draw_rect(pymupdf.Rect(0, 0, 595, 110), color=None, fill=(0.08, 0.16, 0.25))
        page.insert_text((42, 53), "CLIENT DOSSIER", fontsize=25, color=(1, 1, 1))
        page.insert_text((42, 83), "Prepared for sharing", fontsize=11, color=(0.77, 0.84, 0.9))
        page.insert_text((42, 160), "Reference ID: QZ-4819-73", fontsize=16)
        page.insert_text((42, 205), "Project: Northshore Office", fontsize=13)
        page.insert_text((42, 240), "Status: Draft", fontsize=13)
        page.draw_line((42, 265), (553, 265), color=(0.8, 0.84, 0.88))
        page.insert_text((42, 305), "Review notes", fontsize=16)
        page.insert_text((42, 342), "Only the selected area is removed from the saved PDF.", fontsize=11)
        page.insert_text((42, 365), "The remaining text stays readable and searchable.", fontsize=11)
        pdf.save(sample)


def save_capture(widget, output: Path) -> None:
    """Keep published image dimensions stable across display scaling settings."""
    image = widget.grab().toImage()
    image = image.scaled(widget.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    if not image.save(str(output)):
        raise RuntimeError(f"Could not save {output}")


def main() -> None:
    output = PROJECT / "docs/assets"
    output.mkdir(parents=True, exist_ok=True)
    work = PROJECT / "build/readme-preview"
    work.mkdir(parents=True, exist_ok=True)
    sample = work / "preview.pdf"
    create_sample(sample)
    settings_directory = work / "settings"
    settings_directory.mkdir(parents=True, exist_ok=True)
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.IniFormat, scope, str(settings_directory))

    def preview_settings(organization: str, application: str) -> QSettings:
        # The two-string constructor always uses NativeFormat on Windows.
        settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                             organization, application)
        assert settings.format() == QSettings.Format.IniFormat
        assert Path(settings.fileName()).resolve().is_relative_to(settings_directory)
        return settings

    settings = preview_settings("BlurOut PDF", "BlurOut PDF")
    settings.clear()
    for key, value in (("language", "pl"), ("appearance", "dark"),
                       ("redaction_style", "black"), ("ocr_language", "eng")):
        settings.setValue(key, value)
    settings.sync()
    legacy_settings = preview_settings("Rectveil", "Rectveil")
    legacy_settings.clear()
    legacy_settings.sync()

    app = QApplication([])
    app.setApplicationName("BlurOut PDF")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BlurOut PDF")
    app.setStyle("windows11" if "windows11" in QStyleFactory.keys() else "Fusion")
    # Reproduce the documented missing-OCR state without probing external model folders.
    with patch.object(window_module, "QSettings", side_effect=preview_settings), \
            patch.object(search, "_tessdata_directory", return_value=None), \
            patch.object(window_module, "_tessdata_directory", return_value=None):
        window = window_module.MainWindow(str(sample))
        try:
            window._set_zoom(1.0)
            secret = window.document.page(0).search_for("QZ-4819-73")[0]
            window._add_redaction(0, window.document.page_to_display(0, secret))
            window.redact_action.setChecked(True)
            window.resize(1180, 800)
            window.show()
            app.processEvents()
            save_capture(window, output / "ui-preview.png")
        finally:
            window.document.redactions.clear()
            window.close()
    print(f"Captured BlurOut PDF {__version__} in {output.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
