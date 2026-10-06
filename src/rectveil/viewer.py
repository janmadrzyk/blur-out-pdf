"""Continuous PDF pages, painted on demand with bounded image cache."""

from __future__ import annotations

from collections import OrderedDict

import pymupdf
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .document import PdfDocument


PAGE_MARGIN = 14


class PageCanvas(QWidget):
    redaction_drawn = Signal(int, object)

    def __init__(self, viewer: "PdfViewer", index: int) -> None:
        super().__init__()
        self.viewer = viewer
        self.index = index
        self.drag_start: QPoint | None = None
        self.drag_end: QPoint | None = None
        self.setMouseTracking(True)
        self.resize_to_page()

    def resize_to_page(self) -> None:
        width, height = self.viewer.document.display_size(self.index)
        self.setFixedSize(round(width * self.viewer.scale), round(height * self.viewer.scale))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("white"))
        image = self.viewer.get_page_image(self.index)
        if image:
            painter.drawPixmap(self.rect(), image)
        for item in self.viewer.document.redactions:
            if item.page_index == self.index:
                rect = self.viewer.document.page_to_display(self.index, pymupdf.Rect(item.rect))
                target = QRect(round(rect.x0 * self.viewer.scale), round(rect.y0 * self.viewer.scale),
                               round(rect.width * self.viewer.scale), round(rect.height * self.viewer.scale))
                painter.fillRect(target, QColor("#090b0f") if item.style == "black" else QColor("#50565f"))
                painter.setPen(QPen(QColor("#3b9dff"), 1.5, Qt.PenStyle.DashLine))
                painter.drawRect(target)
        for page_index, rect in self.viewer.matches:
            if page_index == self.index:
                display = self.viewer.document.page_to_display(self.index, rect)
                target = QRect(round(display.x0 * self.viewer.scale), round(display.y0 * self.viewer.scale),
                               round(display.width * self.viewer.scale), round(display.height * self.viewer.scale))
                painter.fillRect(target, QColor(255, 203, 75, 110))
        if self.drag_start and self.drag_end:
            target = QRect(self.drag_start, self.drag_end).normalized()
            painter.fillRect(target, QColor(16, 24, 32, 180))
            painter.setPen(QPen(QColor("#3b9dff"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(target)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.viewer.redaction_mode and event.button() == Qt.MouseButton.LeftButton:
            self.drag_start = event.position().toPoint()
            self.drag_end = self.drag_start
            self.update()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_start is not None:
            self.drag_end = event.position().toPoint()
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.drag_start is not None and event.button() == Qt.MouseButton.LeftButton:
            end = event.position().toPoint()
            area = QRect(self.drag_start, end).normalized().intersected(self.rect())
            self.drag_start = self.drag_end = None
            self.update()
            if area.width() >= 3 and area.height() >= 3:
                rect = pymupdf.Rect(area.left() / self.viewer.scale, area.top() / self.viewer.scale,
                                    (area.right() + 1) / self.viewer.scale, (area.bottom() + 1) / self.viewer.scale)
                self.redaction_drawn.emit(self.index, rect)
            event.accept()


class PdfViewer(QScrollArea):
    current_page_changed = Signal(int)
    redaction_drawn = Signal(int, object)

    def __init__(self, document: PdfDocument) -> None:
        super().__init__()
        self.document = document
        self.scale = 1.25
        self.redaction_mode = False
        self.layout_mode = "continuous"
        self.current_page = 0
        self.matches: list[tuple[int, pymupdf.Rect]] = []
        self.cache: OrderedDict[tuple[int, float, float, int], QPixmap] = OrderedDict()
        self.canvases: list[PageCanvas] = []
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.verticalScrollBar().valueChanged.connect(self._detect_current_page)
        self.rebuild()

    def rebuild(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN, PAGE_MARGIN)
        layout.setSpacing(18)
        self.canvases.clear()
        for index in range(self.document.page_count):
            canvas = PageCanvas(self, index)
            canvas.redaction_drawn.connect(self.redaction_drawn)
            layout.addWidget(canvas, alignment=Qt.AlignmentFlag.AlignHCenter)
            self.canvases.append(canvas)
        layout.addStretch()
        old = self.takeWidget()
        self.setWidget(root)
        if old:
            old.deleteLater()
        self._apply_layout_mode()

    def _apply_layout_mode(self) -> None:
        for index, canvas in enumerate(self.canvases):
            canvas.setVisible(self.layout_mode == "continuous" or index == self.current_page)

    def set_layout_mode(self, mode: str) -> None:
        self.layout_mode = mode
        self._apply_layout_mode()
        self.go_to_page(self.current_page)

    def set_scale(self, scale: float) -> None:
        self.scale = max(0.25, min(3.0, scale))
        self.cache.clear()
        for canvas in self.canvases:
            canvas.resize_to_page()
            canvas.update()

    def get_page_image(self, index: int) -> QPixmap | None:
        if not self.document.is_open:
            return None
        device_pixel_ratio = self.devicePixelRatioF()
        key = (index, round(self.scale, 3), round(device_pixel_ratio, 3), self.document.display_rotation(index))
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        # QWidget geometry is in logical pixels. Render the PDF vectors at the
        # corresponding physical display resolution to avoid stretching a
        # low-density pixmap on high-DPI Windows screens.
        pix = self.document.render(index, self.scale * device_pixel_ratio)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        result = QPixmap.fromImage(image)
        result.setDevicePixelRatio(device_pixel_ratio)
        self.cache[key] = result
        if len(self.cache) > 6:
            self.cache.popitem(last=False)
        return result

    def go_to_page(self, index: int) -> None:
        if not self.canvases:
            return
        index = max(0, min(index, len(self.canvases) - 1))
        self.current_page = index
        self._apply_layout_mode()
        self.ensureWidgetVisible(self.canvases[index], 0, 0)
        self.current_page_changed.emit(index)

    def _detect_current_page(self) -> None:
        if self.layout_mode != "continuous" or not self.canvases:
            return
        viewport_center = self.viewport().height() // 2
        distances = [abs(canvas.mapTo(self.viewport(), QPoint(0, canvas.height() // 2)).y() - viewport_center)
                     for canvas in self.canvases]
        index = distances.index(min(distances))
        if index != self.current_page:
            self.current_page = index
            self.current_page_changed.emit(index)

    def show_match(self, page_index: int, rect: pymupdf.Rect) -> None:
        self.go_to_page(page_index)
        canvas = self.canvases[page_index]
        display = self.document.page_to_display(page_index, rect)
        self.verticalScrollBar().setValue(canvas.y() + round(display.y0 * self.scale) - self.viewport().height() // 3)
        canvas.update()

    def refresh_page(self, index: int) -> None:
        self.cache.clear()
        self.canvases[index].resize_to_page()
        self.canvases[index].update()
