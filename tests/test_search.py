import pymupdf

from rectveil.search import _needs_ocr, _tessdata_directory, find_matches, normalized


def test_polish_diacritic_normalization() -> None:
    assert normalized("Łódź", False, True) == "lodz"
    assert normalized("Łódź", False, False) != "lodz"


def test_search_counts_multiword_matches_and_respects_options() -> None:
    document = pymupdf.open()
    first = document.new_page()
    first.insert_text((72, 72), "Alpha beta. alpha beta! alphabet")
    second = document.new_page()
    second.insert_text((72, 72), "alpha beta")

    assert [page for page, _ in find_matches(document, "alpha beta")] == [0, 0, 1]
    assert [page for page, _ in find_matches(document, "Alpha", match_case=True)] == [0]
    assert len(find_matches(document, "alpha", whole_words=True)) == 3
    assert len(find_matches(document, "alpha")) == 4


def test_pending_redaction_hides_only_intersecting_characters() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "secret safe secret")
    chars = page.get_text("rawdict")["blocks"][0]["lines"][0]["spans"][0]["chars"]
    first_secret_middle = pymupdf.Rect(chars[2]["bbox"])
    # A tiny overlap still removes the entire character, as PDF redaction does.
    cover = pymupdf.Rect(first_secret_middle.x0, first_secret_middle.y0,
                         first_secret_middle.x0 + 1, first_secret_middle.y0 + 1)

    original = find_matches(document, "secret")
    filtered = find_matches(document, "secret", hidden_areas={0: [cover]})

    assert len(original) == 2
    assert len(filtered) == 1
    assert filtered[0][1].x0 > original[0][1].x0
    assert find_matches(document, "secret safe", hidden_areas={0: [cover]}) == []
    assert len(find_matches(document, "safe", hidden_areas={0: [cover]})) == 1


def test_search_match_box_covers_only_matching_characters() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "prefix suffix")

    prefix = find_matches(document, "ref")
    whole = find_matches(document, "prefix")

    assert len(prefix) == len(whole) == 1
    assert prefix[0][1].x0 > whole[0][1].x0
    assert prefix[0][1].x1 < whole[0][1].x1


def test_search_finds_clipped_text_in_nested_form_and_filters_redaction() -> None:
    source = pymupdf.open()
    source.new_page().insert_text((72, 72), "Nested secret")
    document = pymupdf.open()
    page = document.new_page()
    page.show_pdf_page(page.rect, source, 0)
    # Wrap the nested Form XObject in a clip that excludes all its text.
    xref = page.get_contents()[0]
    stream = document.xref_stream(xref)
    document.update_stream(xref, b"q\n0 0 1 1 re W n\n" + stream + b"\nQ")
    assert "secret" not in page.get_text()

    matches = find_matches(document, "secret")
    assert len(matches) == 1
    assert page.rect.contains(matches[0][1])
    assert find_matches(document, "secret", hidden_areas={0: [matches[0][1]]}) == []
    assert len(find_matches(document, "Nested", hidden_areas={0: [matches[0][1]]})) == 1


def test_search_finds_hidden_optional_layer_without_changing_visibility() -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Visible secret")
    hidden = document.add_ocg("Hidden personal data", on=False)
    page.insert_text((72, 120), "Nested secret", oc=hidden)
    assert "Nested" not in page.get_text()
    original_layer = document.get_layer()

    matches = find_matches(document, "secret")
    assert len(matches) == 2
    assert matches[1][1].y0 > matches[0][1].y0
    assert len(find_matches(document, "secret", hidden_areas={0: [matches[1][1]]})) == 1
    assert document.get_layer() == original_layer
    assert "Nested" not in page.get_text()


def test_search_uses_ocr_when_page_has_no_extractable_text() -> None:
    if _tessdata_directory() is None:
        import pytest
        pytest.skip("OCR language data is not installed")
    with pymupdf.open() as source:
        page = source.new_page(width=400, height=200)
        page.insert_text((30, 90), "ALPHA ALPHA", fontsize=32)
        image = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")
    with pymupdf.open() as document:
        page = document.new_page(width=400, height=200)
        page.insert_image(page.rect, stream=image)
        assert not page.get_text().strip()
        cache: dict[int, list[dict]] = {}
        matches = find_matches(document, "ALPHA", page_cache=cache)
        assert len(matches) == 2
        assert len(find_matches(document, "ALPHA", hidden_areas={0: [matches[0][1]]},
                                page_cache=cache)) == 1


def test_damaged_character_mapping_triggers_ocr() -> None:
    def blocks(text: str) -> list[dict]:
        return [{"lines": [{"spans": [{"chars": [{"c": char} for char in text]}]}]}]

    assert _needs_ocr(blocks("A\x13\x05\x12"))
    assert not _needs_ocr(blocks("ALPHA BETA"))
