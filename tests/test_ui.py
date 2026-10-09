import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymupdf
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from blurout_pdf.window import MainWindow
from blurout_pdf import search, window as window_module


@pytest.fixture(autouse=True)
def project_local_ocr(monkeypatch) -> None:
    """UI tests must not inspect OCR data outside the project."""
    monkeypatch.setattr(search, "_tessdata_directory", lambda: None)
    monkeypatch.setattr(window_module, "_tessdata_directory", lambda: None)


def test_ocr_language_setting_warns_and_invalidates_search_cache(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    settings_file = tmp_path / "settings.ini"
    monkeypatch.setattr(window_module, "QSettings", lambda *_args: QSettings(
        str(settings_file), QSettings.Format.IniFormat,
    ))
    tessdata = tmp_path / "tessdata"
    tessdata.mkdir()
    (tessdata / "eng.traineddata").touch()
    monkeypatch.setattr(search, "_tessdata_directory", lambda: tessdata)
    monkeypatch.setattr(window_module, "_tessdata_directory", lambda: tessdata)

    source = tmp_path / "source.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 80), "PUBLIC", fontsize=18)
        pdf.save(source)
    window = MainWindow()
    window.open_path(str(source))
    window._active_tab.search_pages[0] = [{"cached": True}]
    window.set_ocr_language("rus")

    assert window.settings.value("ocr_language") == "rus"
    assert window._active_tab.search_pages == {}
    assert "Русский" in window.ocr_notice.text()
    assert window.ocr_actions["rus"].isChecked()

    (tessdata / "rus.traineddata").touch()
    window._refresh_ocr_menu()
    window._refresh_ocr_status()
    assert window.ocr_actions["rus"].isEnabled()
    assert window.ocr_notice.text() == ""
    window.close()
    app.quit()


def test_window_open_search_redact_save(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "source.pdf"
    result = tmp_path / "redacted.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 80), "PUBLIC SECRET", fontsize=18)
        pdf.save(source)
    window = MainWindow()
    window.open_path(str(source))
    window.show()
    app.processEvents()
    assert window.document.page_count == 1
    window.search_field.setText("SECRET")
    assert len(window.matches) == 1
    rect = window.document.page_to_display(0, window.matches[0][1])
    window.redact_action.setChecked(True)
    canvas = window.viewer.canvases[0]
    start = QPoint(round(rect.x0 * window.viewer.scale) - 2, round(rect.y0 * window.viewer.scale) - 2)
    end = QPoint(round(rect.x1 * window.viewer.scale) + 2, round(rect.y1 * window.viewer.scale) + 2)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    assert len(window.document.redactions) == 1
    original_rect = window.document.redactions[0].rect
    redaction_display = window.document.page_to_display(0, pymupdf.Rect(original_rect))
    corner = QPoint(round(redaction_display.x0 * window.viewer.scale),
                    round(redaction_display.y0 * window.viewer.scale))
    resized_corner = QPoint(corner.x() - 10, corner.y() - 10)
    QTest.mouseMove(canvas, corner)
    assert canvas.hovered_redaction == 0
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=corner)
    QTest.mouseMove(canvas, resized_corner)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=resized_corner)
    assert window.document.redactions[0].rect != original_rect
    window.undo_action.trigger()
    assert window.document.redactions[0].rect == original_rect
    window.undo_action.trigger()
    assert not window.document.redactions
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=end)
    assert len(window.document.redactions) == 1
    assert window._save_to(result)
    with pymupdf.open(result) as pdf:
        assert "SECRET" not in pdf[0].get_text()
    window.close()
    app.quit()


def test_document_tabs_keep_search_edits_and_saves_separate(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    saved_second = tmp_path / "second-redacted.pdf"
    for path, text in ((first, "ALPHA SECRET"), (second, "BETA SECRET")):
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((50, 80), text, fontsize=18)
            pdf.save(path)

    window = MainWindow()
    window.open_path(str(first))
    first_document = window.document
    first_viewer = window.viewer
    window.search_field.setText("ALPHA")
    first_secret = first_document.page(0).search_for("SECRET")[0]
    first_document.add_redaction(0, first_secret, "black")
    window._refresh_history_actions()
    window._update_title()

    window.open_path(str(second))
    second_document = window.document
    second_viewer = window.viewer
    assert second_document is not first_document
    assert not second_document.dirty
    window.search_field.setText("BETA")
    second_secret = second_document.page(0).search_for("SECRET")[0]
    second_document.add_redaction(0, second_secret, "black")
    window._refresh_history_actions()

    window.tabs.setCurrentIndex(window.tabs.indexOf(first_viewer))
    assert window.document is first_document
    assert window.search_field.text() == "ALPHA"
    assert len(first_document.redactions) == 1
    window.undo_action.trigger()
    assert not first_document.redactions
    assert len(second_document.redactions) == 1
    window.redo_action.trigger()
    assert len(first_document.redactions) == 1

    window.tabs.setCurrentIndex(window.tabs.indexOf(second_viewer))
    assert window.document is second_document
    assert window.search_field.text() == "BETA"
    assert window._save_to(saved_second)
    assert first_document.dirty
    assert not second_document.dirty
    with pymupdf.open(saved_second) as pdf:
        assert "BETA" in pdf[0].get_text()
        assert "SECRET" not in pdf[0].get_text()
    window.tabs.setCurrentIndex(window.tabs.indexOf(first_viewer))
    window.undo_action.trigger()
    window.tabs.setCurrentIndex(window.tabs.indexOf(second_viewer))
    window.close_tab(window.tabs.indexOf(second_viewer))
    assert window.document is first_document
    window.close_tab(window.tabs.indexOf(first_viewer))
    assert not window.document.is_open
    assert window.tabs.count() == 1
    window.close()
    app.quit()


def test_search_count_and_navigation_update_for_pending_redactions(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "search.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 80), "ALPHA ALPHA BETA", fontsize=18)
        pdf.save(source)

    window = MainWindow()
    window.open_path(str(source))
    window.search_field.setText("ALPHA")
    assert len(window.matches) == 2
    assert window.search_count.text() == "1/2"
    assert window.viewer.matches == window.matches
    window.search_next.click()
    assert window.search_count.text() == "2/2"
    window.search_prev.click()
    assert window.search_count.text() == "1/2"

    first = window.document.page(0).search_for("ALPHA")[0]
    window._add_redaction(0, window.document.page_to_display(0, first))
    assert len(window.matches) == 1
    assert window.search_count.text() == "1/1"
    assert window.matches[0][1].x0 > first.x1
    window.undo_action.trigger()
    assert len(window.matches) == 2
    assert window.search_count.text() == "1/2"
    window.close()
    app.quit()


def test_tab_strip_and_edit_toolbar_controls_are_distinct_and_visible(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "tabs.pdf"
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(source)

    window = MainWindow()
    window.open_path(str(source))
    window.show()
    app.processEvents()

    last_tab = window.tab_bar.tabRect(window.tab_bar.count() - 1)
    assert window.new_tab_button.isVisible()
    assert window.new_tab_button.geometry().left() > last_tab.right()
    close_button = window.tab_bar.tabButton(0, window.tab_bar.ButtonPosition.RightSide)
    assert close_button is not None
    assert close_button.text() == "×"
    assert close_button.objectName() == "tabCloseButton"

    toolbar_controls = [window.edit_toolbar.widgetForAction(action) for action in (
        window.undo_action, window.redo_action, window.metadata_action,
        window.left_action, window.right_action,
    )]
    assert all(control.objectName() == "toolbarControl" for control in toolbar_controls)
    assert window.redact_button.objectName() == "redactButton"
    assert "QTabBar { background:" in app.styleSheet()
    assert "QToolBar QToolButton#toolbarControl" in app.styleSheet()

    window.close()
    app.quit()
