"""Render the appearance of non-black redactions from their source content."""

from __future__ import annotations

import random
from collections.abc import Iterable

import pymupdf
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QBrush, QImage, QPainter, QTransform


SNAPSHOT_SCALE = 3.0  # 216 dpi: detailed enough for printed blur regions.
MAX_PDF_SNAPSHOT_SIDE = 2048
MAX_RASTER_SNAPSHOT_SIDE = 1536  # Bound preview decoding and intermediate Qt images.
COARSE_PIXEL_SCALE = 2.5


def render_blur_png(
    page: pymupdf.Page,
    area: pymupdf.Rect,
    style: str,
    preceding_overlays: Iterable[tuple[pymupdf.Rect, str, bytes | None]] = (),
    raster: bool = False,
) -> bytes:
    """Return a content-derived, pixelated and grained image for a redaction."""
    original_rotation = page.rotation
    page.set_rotation(0)
    try:
        clip = pymupdf.Rect(area) & page.rect
        if clip.is_empty:
            raise ValueError("The redaction area is outside the visible page")
        # Raster pages already have pixel-sized coordinates. Rendering them at
        # 216 DPI tripled both dimensions and made large previews exceed Qt's
        # 256 MB image-decoding limit. Blur intentionally loses fine detail, so
        # a bounded source is sufficient even when the output area is huge.
        max_side = MAX_RASTER_SNAPSHOT_SIDE if raster else MAX_PDF_SNAPSHOT_SIDE
        scale = min(1.0 if raster else SNAPSHOT_SCALE,
                    max_side / max(clip.width, clip.height))
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
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
            round(overlap.x0 * scale - pixmap_x),
            round(overlap.y0 * scale - pixmap_y),
            round(overlap.width * scale),
            round(overlap.height * scale),
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

    blurred = blur_image(source, style, f"{page.number}:{tuple(area)}:{style}", scale)

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


def blur_image(source: QImage, style: str, seed: str, scale: float = SNAPSHOT_SCALE) -> QImage:
    """Apply the same fine or coarse redaction texture to a rendered image."""
    if style not in ("fine", "coarse"):
        raise ValueError(f"Unsupported blur style: {style}")

    points_per_cell = 10 if style == "fine" else 18 * COARSE_PIXEL_SCALE
    cell_pixels = max(1.0, points_per_cell * scale)
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
    grain_step = 2 if style == "fine" else round(7 * COARSE_PIXEL_SCALE)
    # A reusable noise tile avoids a Python loop and a second full-size image.
    # The brush transform sets the visible grain size without enlarging it.
    tile_side = 256
    noise = random.Random(seed).randbytes(tile_side * tile_side)
    grain = QImage(noise, tile_side, tile_side, tile_side, QImage.Format.Format_Grayscale8).copy()
    brush = QBrush(grain)
    brush.setTransform(QTransform().scale(grain_step, grain_step))
    painter = QPainter(blurred)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    painter.setOpacity(0.12 if style == "fine" else 0.24)
    painter.fillRect(blurred.rect(), brush)
    painter.end()

    return blurred
