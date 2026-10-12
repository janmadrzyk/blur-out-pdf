"""Visual feedback for Qt's file picker Details-view drag selection."""

from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QTreeView, QWidget


class FileSelectionMarquee(QWidget):
    """Draw a rectangle without changing the view's selection or mouse events."""

    def __init__(self, view: QTreeView, dark: bool) -> None:
        super().__init__(view.viewport())
        self.setObjectName("fileSelectionMarquee")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._view = view
        self._origin: QPoint | None = None
        self._position: QPoint | None = None
        self.set_dark(dark)
        self.hide()
        view.viewport().installEventFilter(self)
        view.horizontalScrollBar().valueChanged.connect(self._update_rectangle)
        view.verticalScrollBar().valueChanged.connect(self._update_rectangle)

    def set_dark(self, dark: bool) -> None:
        self._color = QColor("#6db5f4" if dark else "#2d77bf")
        self.update()

    def _scroll_offset(self) -> QPoint:
        first = self._view.model().index(0, 0, self._view.rootIndex())
        # The vertical scrollbar may count rows rather than pixels.
        return QPoint(self._view.horizontalScrollBar().value(),
                      -self._view.visualRect(first).top())

    def _clear(self) -> None:
        self._origin = self._position = None
        self.hide()

    def _update_rectangle(self) -> None:
        if self._origin is None or self._position is None:
            return
        origin = self._origin - self._scroll_offset()
        if (not self.isVisible()
                and (self._position - origin).manhattanLength() < QApplication.startDragDistance()):
            return
        self.setGeometry(QRect(origin, self._position).normalized())
        self.show()
        self.raise_()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            self._clear()
            position = event.position().toPoint()
            if (event.button() == Qt.MouseButton.LeftButton
                    and not self._view.indexAt(position).isValid()):
                self._origin = position + self._scroll_offset()
        elif event.type() == QEvent.Type.MouseMove and self._origin is not None:
            if event.buttons() & Qt.MouseButton.LeftButton:
                self._position = event.position().toPoint()
                self._update_rectangle()
            else:
                self._clear()
        elif event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.Hide,
                              QEvent.Type.UngrabMouse, QEvent.Type.WindowDeactivate):
            self._clear()
        elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self._clear()
        return False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        fill = QColor(self._color)
        fill.setAlpha(40)
        painter.fillRect(self.rect(), fill)
        painter.setPen(self._color)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
