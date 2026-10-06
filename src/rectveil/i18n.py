"""Small, explicit UI catalogue. Source identifiers stay in English."""

from PySide6.QtCore import QLocale


STRINGS = {
    "en": {
        "file": "File", "open": "Open…", "save": "Save", "save_as": "Save as…",
        "print": "Print…", "exit": "Exit", "settings": "Settings",
        "language": "Language", "english": "🇬🇧 English", "polish": "🇵🇱 Polski",
        "style": "Redaction style", "black": "Black", "fine": "Fine grain", "coarse": "Coarse grain",
        "toolbar": "Editing toolbar", "show_toolbar": "Show editing toolbar",
        "redact": "Redact", "undo_redaction": "Undo last redaction", "rotate_left": "Rotate left", "rotate_right": "Rotate right",
        "find": "Find…", "find_placeholder": "Find…", "previous_match": "Previous match",
        "next_match": "Next match", "search_options": "Search options", "close_search": "Clear search",
        "case": "Match case", "whole": "Whole words", "diacritics": "Ignore diacritics",
        "first": "First page", "previous": "Previous page", "next": "Next page", "last": "Last page",
        "single": "Single page", "continuous": "Continuous pages", "fit_page": "Fit page",
        "fit_width": "Fit width", "original": "Original size", "zoom": "Zoom",
        "open_pdf": "Open PDF", "save_pdf": "Save PDF", "pdf_filter": "PDF files (*.pdf)",
        "password": "PDF password", "password_prompt": "Enter the password for this PDF:",
        "error": "Error", "incorrect_password": "Could not open the PDF. Check the password or file.",
        "save_error": "The PDF could not be saved: {error}",
        "open_error": "The PDF could not be opened: {error}",
        "unsaved": "Unsaved changes", "unsaved_prompt": "Save changes to the current PDF?",
        "ready": "Open a PDF to start", "drag_hint": "Drag a rectangle on a page to redact",
        "saved": "Saved: {path}", "no_results": "No matches", "matches": "{current} of {total}",
        "page_of": "{current}/{total}", "redaction_added": "Redaction added. Save the PDF to remove its content.",
        "nothing_to_print": "Open a PDF first.",
    },
    "pl": {
        "file": "Plik", "open": "Otwórz…", "save": "Zapisz", "save_as": "Zapisz jako…",
        "print": "Drukuj…", "exit": "Zakończ", "settings": "Ustawienia",
        "language": "Język", "english": "🇬🇧 English", "polish": "🇵🇱 Polski",
        "style": "Styl cenzury", "black": "Czarny", "fine": "Drobne ziarno", "coarse": "Grube ziarno",
        "toolbar": "Pasek edycji", "show_toolbar": "Pokaż pasek edycji",
        "redact": "Cenzuruj", "undo_redaction": "Cofnij ostatnią cenzurę", "rotate_left": "Obróć w lewo", "rotate_right": "Obróć w prawo",
        "find": "Znajdź…", "find_placeholder": "Znajdź…", "previous_match": "Poprzedni wynik",
        "next_match": "Następny wynik", "search_options": "Opcje wyszukiwania", "close_search": "Wyczyść wyszukiwanie",
        "case": "Rozróżniaj wielkość liter", "whole": "Całe wyrazy", "diacritics": "Ignoruj znaki diakrytyczne",
        "first": "Pierwsza strona", "previous": "Poprzednia strona", "next": "Następna strona", "last": "Ostatnia strona",
        "single": "Jedna strona", "continuous": "Strony ciągłe", "fit_page": "Dopasuj stronę",
        "fit_width": "Dopasuj szerokość", "original": "Oryginalny rozmiar", "zoom": "Powiększenie",
        "open_pdf": "Otwórz PDF", "save_pdf": "Zapisz PDF", "pdf_filter": "Pliki PDF (*.pdf)",
        "password": "Hasło PDF", "password_prompt": "Podaj hasło do tego pliku PDF:",
        "error": "Błąd", "incorrect_password": "Nie można otworzyć PDF. Sprawdź hasło lub plik.",
        "save_error": "Nie udało się zapisać PDF: {error}",
        "open_error": "Nie udało się otworzyć PDF: {error}",
        "unsaved": "Niezapisane zmiany", "unsaved_prompt": "Zapisać zmiany w bieżącym PDF?",
        "ready": "Otwórz PDF, aby zacząć", "drag_hint": "Narysuj prostokąt na stronie, aby zakryć treść",
        "saved": "Zapisano: {path}", "no_results": "Brak wyników", "matches": "{current} z {total}",
        "page_of": "{current}/{total}", "redaction_added": "Dodano cenzurę. Zapisz PDF, aby usunąć treść.",
        "nothing_to_print": "Najpierw otwórz PDF.",
    },
}


def default_language() -> str:
    language = QLocale.system().name().lower()
    return "pl" if language.startswith("pl") else "en"


def translate(language: str, key: str, **values: object) -> str:
    return STRINGS.get(language, STRINGS["en"]).get(key, key).format(**values)
