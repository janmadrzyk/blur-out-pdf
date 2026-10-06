"""PDF operations. UI coordinates never enter this module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import random
import tempfile

import pymupdf


STYLES = ("black", "fine", "coarse")


@dataclass(frozen=True)
class Redaction:
    page_index: int
    rect: tuple[float, float, float, float]
    style: str = "black"


class PdfDocument:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.pdf: pymupdf.Document | None = None
        self.redactions: list[Redaction] = []
        self.rotations: dict[int, int] = {}

    @property
    def is_open(self) -> bool:
        return self.pdf is not None

    @property
    def dirty(self) -> bool:
        return bool(self.redactions or self.rotations)

    @property
    def page_count(self) -> int:
        return len(self.pdf) if self.pdf else 0

    def open(self, path: str | Path, password: str | None = None) -> bool:
        candidate = pymupdf.open(str(path))
        if not candidate.is_pdf:
            candidate.close()
            raise ValueError("Only PDF files are supported")
        if candidate.needs_pass:
            if password is None:
                candidate.close()
                return False
            if not candidate.authenticate(password):
                candidate.close()
                raise ValueError("Incorrect PDF password")
        if self.pdf:
            self.pdf.close()
        self.pdf = candidate
        self.path = Path(path)
        self.redactions.clear()
        self.rotations.clear()
        return True

    def close(self) -> None:
        if self.pdf:
            self.pdf.close()
        self.pdf = None
        self.path = None
        self.redactions.clear()
        self.rotations.clear()

    def page(self, index: int) -> pymupdf.Page:
        if self.pdf is None:
            raise RuntimeError("No PDF is open")
        return self.pdf.load_page(index)

    def display_rotation(self, index: int) -> int:
        page = self.page(index)
        return (page.rotation + self.rotations.get(index, 0)) % 360

    def display_size(self, index: int) -> tuple[float, float]:
        page = self.page(index)
        width, height = page.rect.width, page.rect.height
        if self.rotations.get(index, 0) % 180:
            return height, width
        return width, height

    def display_to_page(self, index: int, rect: pymupdf.Rect) -> pymupdf.Rect:
        """Map a rectangle in the pending-rotation display to PDF page space."""
        page = self.page(index)
        original_rotation = page.rotation
        page.set_rotation(self.display_rotation(index))
        try:
            result = rect * page.derotation_matrix
        finally:
            page.set_rotation(original_rotation)
        return result & page.cropbox

    def page_to_display(self, index: int, rect: pymupdf.Rect) -> pymupdf.Rect:
        page = self.page(index)
        original_rotation = page.rotation
        page.set_rotation(self.display_rotation(index))
        try:
            return rect * page.rotation_matrix
        finally:
            page.set_rotation(original_rotation)

    def add_redaction(self, page_index: int, display_rect: pymupdf.Rect, style: str) -> None:
        if style not in STYLES:
            raise ValueError(style)
        rect = self.display_to_page(page_index, display_rect)
        if rect.width < 2 or rect.height < 2:
            return
        self.redactions.append(Redaction(page_index, tuple(rect), style))

    def rotate(self, page_index: int, degrees: int) -> None:
        if degrees not in (-90, 90):
            raise ValueError(degrees)
        value = (self.rotations.get(page_index, 0) + degrees) % 360
        if value:
            self.rotations[page_index] = value
        else:
            self.rotations.pop(page_index, None)

    def undo_last_redaction(self) -> int | None:
        return self.redactions.pop().page_index if self.redactions else None

    def render(self, index: int, scale: float = 1.0) -> pymupdf.Pixmap:
        page = self.page(index)
        original_rotation = page.rotation
        page.set_rotation(self.display_rotation(index))
        try:
            return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        finally:
            page.set_rotation(original_rotation)

    def save(self, target: str | Path) -> None:
        """Write a full replacement PDF, then atomically replace the destination."""
        if self.pdf is None:
            raise RuntimeError("No PDF is open")
        destination = Path(target).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Work on a private copy so a failed save cannot alter the open document.
        copy = pymupdf.open(stream=self.pdf.tobytes(), filetype="pdf")
        temporary: Path | None = None
        try:
            for index, delta in self.rotations.items():
                page = copy.load_page(index)
                page.set_rotation((page.rotation + delta) % 360)
            for redaction in self.redactions:
                page = copy.load_page(redaction.page_index)
                page.add_redact_annot(pymupdf.Rect(redaction.rect), fill=(0, 0, 0), cross_out=False)
            for index in sorted({item.page_index for item in self.redactions}):
                page = copy.load_page(index)
                page.apply_redactions(
                    images=pymupdf.PDF_REDACT_IMAGE_PIXELS,
                    graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                    text=pymupdf.PDF_REDACT_TEXT_REMOVE,
                )
            for redaction in self.redactions:
                if redaction.style != "black":
                    self._draw_grain(copy.load_page(redaction.page_index), redaction)
            # Remove common hidden data that could contain another copy of a secret.
            if self.redactions:
                copy.scrub(
                    attached_files=True, embedded_files=True, hidden_text=True,
                    javascript=True, metadata=True, xml_metadata=True,
                    remove_links=True, reset_fields=True, reset_responses=True,
                    thumbnails=True, redactions=False,
                )
            with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="rectveil-", dir=destination.parent, delete=False) as handle:
                temporary = Path(handle.name)
            copy.save(str(temporary), garbage=4, clean=True, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
            # A failed reopen must never replace the user's existing file.
            verification = pymupdf.open(str(temporary))
            try:
                if verification.page_count != self.page_count:
                    raise RuntimeError("Saved PDF has an unexpected page count")
                for redaction in self.redactions:
                    area = pymupdf.Rect(redaction.rect)
                    for block in verification[redaction.page_index].get_text("rawdict")["blocks"]:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                for char in span.get("chars", []):
                                    if pymupdf.Rect(char["bbox"]).intersects(area):
                                        raise RuntimeError("Text remains in a redacted area")
            finally:
                verification.close()
            replacing_open_file = self.path is not None and self.path.resolve() == destination
            if replacing_open_file:
                self.pdf.close()
                self.pdf = None
            try:
                os.replace(temporary, destination)
            except Exception:
                if replacing_open_file:
                    self.pdf = pymupdf.open(str(destination))
                raise
            temporary = None
        finally:
            copy.close()
            if temporary and temporary.exists():
                temporary.unlink()
        self.open(destination)

    @staticmethod
    def _draw_grain(page: pymupdf.Page, redaction: Redaction) -> None:
        """Decorative noise is generated independently from the removed content."""
        rect = pymupdf.Rect(redaction.rect)
        width = max(1, min(1600, round(rect.width)))
        height = max(1, min(1600, round(rect.height)))
        step = 2 if redaction.style == "fine" else 7
        rng = random.Random(f"{redaction.page_index}:{redaction.rect}:{redaction.style}")
        samples = bytearray()
        for y in range(0, height, step):
            row = bytearray()
            for x in range(0, width, step):
                shade = rng.randint(38, 125)
                row.extend(bytes((shade, shade, shade)) * min(step, width - x))
            samples.extend(row * min(step, height - y))
        image = pymupdf.Pixmap(pymupdf.csRGB, width, height, bytes(samples), False)
        page.insert_image(rect, stream=image.tobytes("png"), overlay=True)
