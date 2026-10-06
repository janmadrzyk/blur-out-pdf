"""Render the appearance of non-black redactions from their source content."""

from __future__ import annotations

import random
from collections.abc import Iterable

import pymupdf
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QImage, QPainter


SNAPSHOT_SCALE = 3.0  # 216 dpi: detailed enough for printed blur regions.


def render_blur_png(
    page: pymupdf.Page,
    area: pymupdf.Rect,
    style: str,
    preceding_overlays: Iterable[tuple[pymupdf.Rect, str, bytes | None]] = (),
) -> bytes:
    """Return a content-derived, pixelated and grained image for a redaction."""
    original_rotation = page.rotation
    page.set_rotation(0)
    try:
        clip = pymupdf.Rect(area) & page.rect
        if clip.is_empty:
            raise ValueError("The redaction area is outside the visible page")
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(SNAPSHOT_SCALE, SNAPSHOT_SCALE), clip=clip, alpha=False,
        )
    finally:
        page.set_rotation(original_rotation)

    source = QImage(
        pixmap.samples, pixmap.width, pixmap.height, pixmap.stride,
        QImage.Format.Format_RGB888,
    ).copy()
    if source.isNull():
        raise RuntimeError("Could not render the contents under the redaction")

    painter = QPainter(source)
    for overlay_rect, overlay_style, overlay_data in preceding_overlays:
        overlap = pymupdf.Rect(area) & pymupdf.Rect(overlay_rect)
        if overlap.is_empty:
            continue
        pixmap_x, pixmap_y = pixmap.irect[:2]
        target = QRect(
            round(overlap.x0 * SNAPSHOT_SCALE - pixmap_x),
            round(overlap.y0 * SNAPSHOT_SCALE - pixmap_y),
            round(overlap.width * SNAPSHOT_SCALE),
            round(overlap.height * SNAPSHOT_SCALE),
        ).intersected(source.rect())
        if target.isEmpty():
            continue
        if overlay_style == "black" or not overlay_data:
            painter.fillRect(target, Qt.GlobalColor.black)
        else:
            overlay_image = QImage.fromData(overlay_data, "PNG")
            if overlay_image.isNull():
                painter.fillRect(target, Qt.GlobalColor.black)
                continue
            source_x = round((overlap.x0 - overlay_rect.x0) / overlay_rect.width * overlay_image.width())
            source_y = round((overlap.y0 - overlay_rect.y0) / overlay_rect.height * overlay_image.height())
            source_width = round(overlap.width / overlay_rect.width * overlay_image.width())
            source_height = round(overlap.height / overlay_rect.height * overlay_image.height())
            source_rect = QRect(source_x, source_y, source_width, source_height).intersected(overlay_image.rect())
            painter.drawImage(target, overlay_image.copy(source_rect))
    painter.end()

    points_per_cell = 10 if style == "fine" else 18
    cell_pixels = points_per_cell * SNAPSHOT_SCALE
    small = source.scaled(
        max(1, round(source.width() / cell_pixels)),
        max(1, round(source.height() / cell_pixels)),
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    blurred = small.scaled(
        source.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    # Add a fine or coarse deterministic texture to make the two blur styles
    # visibly distinct while obscuring the rendered source.
    grain_step = 2 if style == "fine" else 7
    grain_width = max(1, (source.width() + grain_step - 1) // grain_step)
    grain_height = max(1, (source.height() + grain_step - 1) // grain_step)
    rng = random.Random(f"{page.number}:{tuple(area)}:{style}")
    rgba = bytearray(grain_width * grain_height * 4)
    for offset in range(0, len(rgba), 4):
        shade = rng.randrange(40, 216)
        rgba[offset:offset + 4] = bytes((shade, shade, shade, 255))
    grain = QImage(
        rgba, grain_width, grain_height, grain_width * 4,
        QImage.Format.Format_RGBA8888,
    ).copy().scaled(
        source.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,
    )
    painter = QPainter(blurred)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
    painter.setOpacity(0.12 if style == "fine" else 0.24)
    painter.drawImage(0, 0, grain)
    painter.end()

    encoded = QByteArray()
    buffer = QBuffer(encoded)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise RuntimeError("Could not encode the redaction preview")
    try:
        if not blurred.save(buffer, "PNG"):
            raise RuntimeError("Could not encode the redaction preview")
    finally:
        buffer.close()
    return bytes(encoded)
