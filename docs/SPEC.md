# Rectveil technical specification (draft, 0.1)

## Purpose and scope

The application lets a Windows user read a PDF, draw rectangular redactions, and export a PDF in which page content within those rectangles is removed. The first usable slice is intentionally small: open, scroll, search, navigate, zoom, rotate, redact, undo the last pending redaction, save and change language/style. Printing, facing-page layouts, full edit history and a custom app icon are later slices.

The product name is provisional. Candidates for the final name: **Rectveil** (current), **QuietRect**, **ShadePage**, **Blackleaf**. A web search found an existing PDF project named VeilPDF and existing products named RedactDesk, CloakPDF and PageVeil, so those names were avoided. A formal trademark check has not been done.

## User flow

1. File → Open or pass a PDF path on the command line. Prompt for a password when required. An unsupported or corrupt file produces an error and does not replace the current document.
2. Read by vertical scrolling. The bottom bar supports first/previous/next/last page, typed page number, single/continuous mode, zoom presets, fit page/width and a linked slider. Ctrl+F focuses search; options include case, whole words and diacritics.
3. Select a cover style under Settings. Activate **Redact**, then drag a rectangle with the left mouse button. Show a visible pending region; allow multiple regions on a page and across pages. Ctrl+Z removes the last pending redaction. Rotations can be changed before saving.
4. Save overwrites the opened path; Save as suggests a `-redacted.pdf` copy. The exporter writes a separate temporary PDF, verifies page count and absence of extractable characters in the selected areas, then replaces the destination. A failed export leaves the existing destination intact.

## Architecture and data contracts

- `document.py` owns the open PyMuPDF document, pending redactions and pending rotations. Redaction rectangles are stored in unrotated PDF page coordinates as `(x0, y0, x1, y1)` point values, with a page index and style. Display coordinates are converted with the page rotation/derotation matrices.
- `viewer.py` creates one lightweight widget per page, renders visible pages on demand and retains at most six rendered page images. It owns only view state (zoom, layout mode, current page, highlight rectangles).
- `window.py` owns menus, actions and dialogs. It saves only language and cover style in `QSettings`. `i18n.py` contains English/Polish strings; source identifiers and repository content remain English.
- `search.py` normalizes text for case/diacritic options and finds words or phrases within a line. It currently does not find phrases across line or page breaks.

## Redaction and privacy behavior

- Use `Page.add_redact_annot()` and `Page.apply_redactions()` to remove intersecting text characters, overlapping image pixels and touched vector graphics. A grain style adds generated neutral squares only after removal. It never reuses blurred source pixels.
- Apply rotations and save with `garbage=4`, `clean=True`, `deflate=True`, without incremental updates. When redactions are present, remove common hidden data with `Document.scrub()`: metadata, attachments, scripts, links and form responses. A redaction save therefore removes those features when they existed in the original document.
- Reopen the temporary PDF and reject it if the page count differs or extractable text characters intersect a selected rectangle. This is a bounded verification, not a proof that arbitrary PDF objects or duplicate secrets outside the selected areas do not exist.
- The source document remains untouched until Save intentionally replaces it. Save as writes a separate destination. There is no network processing or telemetry.

## UI and visual system

Use native Qt widgets with a restrained Windows-style palette: light surfaces `#ffffff/#f3f5f8`, dark surfaces `#171b22/#222832`, blue `#2d77bf` for active controls, and a single 24 px stroke-icon family. All controls have text or tooltips. The top menu has File and Settings; the search field sits at the right, following the supplied screenshot's field, arrows and option menu. The editing toolbar can be hidden. The bottom bar centers page navigation and places page mode and zoom on the right. The two requested page-mode icons currently mean single and continuous; facing modes are deferred until their behavior is implemented.

The operating-system color scheme is read when the window opens. A future slice should respond live to theme changes. The final program icon is pending user artwork.

## Packaging and licensing

Python 3.11+, PySide6 and PyMuPDF. PyInstaller builds a Windows app directory; Inno Setup packages it into one installer and adds an Open with registration for PDF without changing the user's default viewer. Source and distribution use AGPL-3.0-only to match the open-source route for PyMuPDF. Before public release, perform a dependency notice and installer verification pass.

## Verification and remaining work

Automated tests create PDF fixtures and check text removal, metadata/attachment removal, rotation, in-place replacement and the UI open/search/save path. Manual checks should cover a multi-page PDF, mouse drawing, each grain style, Polish and English, light and dark Windows modes, password handling, zoom fit, installer registration and re-opening a saved output in an independent PDF reader. Further security tests need scanned images, reused image objects, layered/vector PDFs, forms, signatures, annotations and maliciously malformed files. A large-file performance pass and accessible keyboard workflow are also pending.
