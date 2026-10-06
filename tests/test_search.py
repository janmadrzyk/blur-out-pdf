from rectveil.search import normalized


def test_polish_diacritic_normalization() -> None:
    assert normalized("Łódź", False, True) == "lodz"
    assert normalized("Łódź", False, False) != "lodz"
