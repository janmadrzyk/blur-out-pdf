"""Text search with case, whole-word and accent options."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence

import pymupdf


def normalized(value: str, match_case: bool, ignore_diacritics: bool) -> str:
    if ignore_diacritics:
        value = value.translate(str.maketrans({"ł": "l", "Ł": "L"}))
        value = "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")
    return value if match_case else value.casefold()


def find_matches(
    document: pymupdf.Document,
    query: str,
    match_case: bool = False,
    whole_words: bool = False,
    ignore_diacritics: bool = False,
    hidden_areas: Mapping[int, Sequence[pymupdf.Rect]] | None = None,
) -> list[tuple[int, pymupdf.Rect]]:
    needle = normalized(" ".join(query.split()), match_case, ignore_diacritics)
    if not needle:
        return []
    results: list[tuple[int, pymupdf.Rect]] = []
    for page_index, page in enumerate(document):
        areas = hidden_areas.get(page_index, ()) if hidden_areas else ()
        for block in page.get_text("rawdict", sort=True)["blocks"]:
            for line in block.get("lines", []):
                # Keep one rectangle per normalized character. A redacted
                # character is a barrier, so a query cannot bridge over it.
                characters: list[str] = []
                boxes: list[pymupdf.Rect | None] = []
                for span in line.get("spans", []):
                    for char in span.get("chars", []):
                        box = pymupdf.Rect(char["bbox"])
                        if any(box.intersects(area) for area in areas):
                            characters.append("\0")
                            boxes.append(None)
                            continue
                        value = normalized(char["c"], match_case, ignore_diacritics)
                        for part in value:
                            characters.append(" " if part.isspace() else part)
                            boxes.append(box)
                haystack = "".join(characters)
                offset = 0
                while (start := haystack.find(needle, offset)) >= 0:
                    end = start + len(needle)
                    left_ok = start == 0 or not haystack[start - 1].isalnum()
                    right_ok = end == len(haystack) or not haystack[end].isalnum()
                    if not whole_words or (left_ok and right_ok):
                        matching = [box for box in boxes[start:end] if box is not None]
                        if matching:
                            rect = pymupdf.Rect(matching[0])
                            for box in matching[1:]:
                                rect |= box
                            results.append((page_index, rect))
                    offset = start + 1
    return results
