import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pymupdf
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from rectveil.window import MainWindow


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
