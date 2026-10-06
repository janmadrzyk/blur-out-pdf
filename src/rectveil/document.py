"""PDF operations. UI coordinates never enter this module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import random
import tempfile

import pymupdf

from .metadata import METADATA_FIELDS


STYLES = ("black", "fine", "coarse")


@dataclass(frozen=True)
class Redaction:
    page_index: int
    rect: tuple[float, float, float, float]
    style: str = "black"


EditState = tuple[Redaction, ...]


class PdfDocument:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.pdf: pymupdf.Document | None = None
        self.redactions: list[Redaction] = []
        self.rotations: dict[int, int] = {}
        self._undo_states: list[EditState] = []
        self._redo_states: list[EditState] = []
        self._metadata_cleared = False
        self._metadata_overrides: dict[str, str] = {}
        self._xml_metadata_override: str | None = None

    @property
    def is_open(self) -> bool:
        return self.pdf is not None

    @property
    def dirty(self) -> bool:
        return bool(self.redactions or self.rotations or self._metadata_cleared
                    or self._metadata_overrides or self._xml_metadata_override is not None)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_states)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_states)

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
        self._undo_states.clear()
        self._redo_states.clear()
        self._metadata_cleared = False
        self._metadata_overrides.clear()
        self._xml_metadata_override = None
        return True

    def close(self) -> None:
        if self.pdf:
            self.pdf.close()
        self.pdf = None
        self.path = None
        self.redactions.clear()
        self.rotations.clear()
        self._undo_states.clear()
        self._redo_states.clear()
        self._metadata_cleared = False
        self._metadata_overrides.clear()
        self._xml_metadata_override = None

    def metadata_values(self) -> dict[str, str]:
        if self.pdf is None:
            return {key: "" for key in METADATA_FIELDS}
        source = self.pdf.metadata or {}
        if self._metadata_cleared:
            values = {key: "" for key in METADATA_FIELDS}
        else:
            values = {key: self._metadata_text(source.get(key)) for key in METADATA_FIELDS}
        values.update(self._metadata_overrides)
        return values

    def technical_metadata(self) -> dict[str, str]:
        if self.pdf is None:
            return {}
        source = self.pdf.metadata or {}
        return {key: self._metadata_text(source.get(key)) for key in ("format", "encryption")}

    def xml_metadata_text(self) -> str:
        if self._xml_metadata_override is not None:
            return self._xml_metadata_override
        return self.pdf.get_xml_metadata() if self.pdf is not None else ""

    def apply_metadata_edits(
        self,
        values: dict[str, str],
        xml_metadata: str | None = None,
        clear_all: bool = False,
    ) -> None:
        if self.pdf is None:
            raise RuntimeError("No PDF is open")
        if clear_all:
            self._metadata_cleared = True
        original = self.pdf.metadata or {}
        if self._metadata_cleared:
            self._metadata_overrides = {
                key: value for key, value in values.items()
                if key in METADATA_FIELDS and value != ""
            }
        else:
            self._metadata_overrides = {
                key: value for key, value in values.items()
                if key in METADATA_FIELDS and value != self._metadata_text(original.get(key))
            }
        if clear_all:
            xml_metadata = xml_metadata if xml_metadata is not None else ""
        if xml_metadata is not None:
            original_xml = self.pdf.get_xml_metadata()
            self._xml_metadata_override = None if xml_metadata == original_xml and not self._metadata_cleared else xml_metadata

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
        self._record_content_edit()
        self.redactions.append(Redaction(page_index, tuple(rect), style))

    def rotate(self, page_index: int, degrees: int) -> None:
        if degrees not in (-90, 90):
            raise ValueError(degrees)
        value = (self.rotations.get(page_index, 0) + degrees) % 360
        if value:
            self.rotations[page_index] = value
        else:
            self.rotations.pop(page_index, None)

    def undo(self) -> set[int]:
        if not self._undo_states:
            return set()
        self._redo_states.append(self._content_state())
        return self._restore_content_state(self._undo_states.pop())

    def redo(self) -> set[int]:
        if not self._redo_states:
            return set()
        self._undo_states.append(self._content_state())
        return self._restore_content_state(self._redo_states.pop())

    def undo_last_redaction(self) -> int | None:
        """Compatibility wrapper for callers of the original one-step undo."""
        changed_pages = self.undo()
        return min(changed_pages) if changed_pages else None

    def _content_state(self) -> EditState:
        return tuple(self.redactions)

    def _record_content_edit(self) -> None:
        self._undo_states.append(self._content_state())
        self._redo_states.clear()

    def _restore_content_state(self, state: EditState) -> set[int]:
        previous_redactions = self.redactions
        next_redactions = state
        page_indexes = {item.page_index for item in (*previous_redactions, *next_redactions)}
        changed = {
            index for index in page_indexes
            if ([item for item in previous_redactions if item.page_index == index]
                != [item for item in next_redactions if item.page_index == index])
        }
        self.redactions = list(next_redactions)
        return changed

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
            # Run general cleanup before redaction so it remains the final
            # content-removal pass on page text and form appearances.
            if self.redactions:
                copy.scrub(
                    attached_files=True, embedded_files=True, hidden_text=True,
                    javascript=True, metadata=True, xml_metadata=True,
                    remove_links=True, reset_fields=True, reset_responses=True,
                    thumbnails=True, redactions=False,
                )
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
            if self._metadata_cleared:
                # Removing the whole Info dictionary also drops vendor-specific keys.
                copy.xref_set_key(-1, "Info", "null")
                copy.del_xml_metadata()
                if self._metadata_overrides:
                    copy.set_metadata(self._metadata_overrides)
            elif self._metadata_overrides:
                metadata = {} if self.redactions else dict(copy.metadata or {})
                metadata.update(self._metadata_overrides)
                copy.set_metadata(metadata)
            if self._xml_metadata_override is not None:
                if self._xml_metadata_override:
                    copy.set_xml_metadata(self._xml_metadata_override)
                else:
                    copy.del_xml_metadata()
            with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="rectveil-", dir=destination.parent, delete=False) as handle:
                temporary = Path(handle.name)
            copy.save(str(temporary), garbage=4, clean=True, deflate=True, encryption=pymupdf.PDF_ENCRYPT_NONE)
            # A failed reopen must never replace the user's existing file.
            verification = pymupdf.open(str(temporary))
            try:
                if verification.page_count != self.page_count:
                    raise RuntimeError("Saved PDF has an unexpected page count")
                if self._metadata_cleared and not self._metadata_overrides:
                    if verification.xref_get_key(-1, "Info")[0] != "null":
                        raise RuntimeError("Metadata remains in the saved PDF")
                for key, expected in self._metadata_overrides.items():
                    actual = self._metadata_text((verification.metadata or {}).get(key))
                    if actual != expected:
                        raise RuntimeError("Metadata was not saved correctly")
                if self._metadata_cleared or self._xml_metadata_override == "":
                    if verification.get_xml_metadata():
                        raise RuntimeError("XML metadata remains in the saved PDF")
                for redaction in self.redactions:
                    area = pymupdf.Rect(redaction.rect)
                    for block in verification[redaction.page_index].get_text("rawdict")["blocks"]:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                for char in span.get("chars", []):
                                    if pymupdf.Rect(char["bbox"]).intersects(area):
                                        raise RuntimeError(
                                            f"Text remains in a redacted area on page {redaction.page_index + 1}"
                                        )
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
    def _metadata_text(value: object) -> str:
        return "" if value is None or str(value).lower() == "none" else str(value)

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
