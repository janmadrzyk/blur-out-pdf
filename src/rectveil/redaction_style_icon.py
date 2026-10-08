"""Toolbar previews for the currently selected redaction style."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap

from .redaction_visual import SNAPSHOT_SCALE, blur_image


ICON_WIDTH = 44
ICON_HEIGHT = 22
PIXEL_RATIO = 2
LETTER_BITMAPS = (
    ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),  # B
    ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),  # L
    ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),  # U
    ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),  # R
)


@lru_cache(maxsize=6)
def redaction_style_icon(style: str, dark: bool) -> QIcon:
    """Show black fill or the same blur texture used on PDF redactions."""
    if style not in ("black", "fine", "coarse"):
        raise ValueError(f"Unsupported redaction style: {style}")

    width = ICON_WIDTH * PIXEL_RATIO
    height = ICON_HEIGHT * PIXEL_RATIO
    result = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    if style == "black":
        painter.fillRect(result.rect(), Qt.GlobalColor.black)
        # All style previews occupy the same rectangle, including black fill.
        painter.setPen(QPen(QColor("#a8b0bc" if dark else "#1d2633"), 2))
        painter.drawRect(result.rect().adjusted(0, 0, -1, -1))
    else:
        # Use the PDF snapshot scale so the word has realistic text dimensions.
        # Oversampling the source enlarges the letters relative to the blur cells
        # and makes the icon readable, unlike a redaction of normal-sized text.
        source = QImage(round(ICON_WIDTH * SNAPSHOT_SCALE),
                        round(ICON_HEIGHT * SNAPSHOT_SCALE), QImage.Format.Format_RGB32)
        source.fill(QColor("#222832" if dark else "#ffffff"))
        sample = QPainter(source)
        ink = QColor("#edf1f7" if dark else "#1d2633")
        unit = 5
        left = (source.width() - 23 * unit) // 2
        top = (source.height() - 7 * unit) // 2
        for letter_index, rows in enumerate(LETTER_BITMAPS):
            for row_index, row in enumerate(rows):
                for column_index, pixel in enumerate(row):
                    if pixel == "1":
                        sample.fillRect(
                            QRect(left + (letter_index * 6 + column_index) * unit,
                                  top + row_index * unit, unit, unit),
                            ink,
                        )
        sample.end()

        preview = blur_image(source, style, f"toolbar:{style}:{dark}")
        painter.drawImage(result.rect(), preview)
        painter.setPen(QPen(QColor("#647084" if dark else "#b3bdca"), 2))
        painter.drawRect(result.rect().adjusted(0, 0, -1, -1))
    painter.end()

    pixmap = QPixmap.fromImage(result)
    pixmap.setDevicePixelRatio(PIXEL_RATIO)
    return QIcon(pixmap)
