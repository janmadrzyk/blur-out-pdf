"""Text search with case, whole-word and accent options."""

from __future__ import annotations

import unicodedata

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
) -> list[tuple[int, pymupdf.Rect]]:
    needle = normalized(query.strip(), match_case, ignore_diacritics)
    if not needle:
        return []
    results: list[tuple[int, pymupdf.Rect]] = []
    for page_index, page in enumerate(document):
        words = page.get_text("words", sort=True)
        # Join adjacent words on a line so ordinary multi-word queries work.
        groups: dict[tuple[int, int], list[tuple]] = {}
        for word in words:
            groups.setdefault((int(word[5]), int(word[6])), []).append(word)
        for line in groups.values():
            line.sort(key=lambda item: item[7])
            pieces = [normalized(str(item[4]), match_case, ignore_diacritics) for item in line]
            haystack = " ".join(pieces)
            offsets = []
            cursor = 0
            for piece in pieces:
                offsets.append((cursor, cursor + len(piece)))
                cursor += len(piece) + 1
            offset = 0
            while (start := haystack.find(needle, offset)) >= 0:
                end = start + len(needle)
                left_ok = start == 0 or not haystack[start - 1].isalnum()
                right_ok = end == len(haystack) or not haystack[end].isalnum()
                if not whole_words or (left_ok and right_ok):
                    matching = [item for item, (a, b) in zip(line, offsets) if a < end and b > start]
                    if matching:
                        rect = pymupdf.Rect(matching[0][:4])
                        for item in matching[1:]:
                            rect |= pymupdf.Rect(item[:4])
                        results.append((page_index, rect))
                offset = start + max(1, len(needle))
    return results
