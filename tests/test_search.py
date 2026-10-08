import pymupdf

from rectveil.search import find_matches, normalized


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
