# BlurOut PDF technical specification (draft, 0.1)

## Purpose and scope

The application lets a Windows user read PDFs and raster images, draw rectangular redactions, and save a rewritten document. For PDFs, content in selected regions is removed. For raster images, covered pixels are rewritten in the output. The supported raster formats are JPEG/JPG, PNG, TIFF, BMP and WebP. The UI supports open, scroll, navigate, zoom, rotate, redact, undo the last pending redaction, save and change language/style. Search is available only for PDFs.

The product name is **BlurOut PDF**. The Windows executable is `BlurOutPDF.exe`, and the Python package is `blurout_pdf`.

## User flow

1. File → Open or pass a supported file path on the command line. Prompt for a password when a PDF requires one. An unsupported or corrupt file produces an error and does not replace the current document.
2. Read by vertical scrolling. The bottom bar supports first/previous/next/last page, typed page number, single/continuous mode, zoom presets, fit page/width and a linked slider. Ctrl+F and the search field are disabled for raster documents; PDF search options include case, whole words and diacritics.
3. Select a cover style under Settings. Activate **Redact**, then drag a rectangle with the left mouse button. Show a visible pending region; allow multiple regions on a page and across pages. Ctrl+Z removes the last pending redaction. Rotations can be changed before saving.
4. PDF Save overwrites the opened path; Save as suggests a `-redacted.pdf` copy. The exporter writes a separate temporary PDF, verifies page count and absence of extractable characters in the selected areas, then replaces the destination. Raster Save rewrites the opened path in its existing format. Single-image raster Save as switches the open tab to the new file. Converting a multi-page TIFF to PNG, JPEG, BMP or WebP writes numbered files in a dedicated folder; the TIFF tab stays open and retains its pending changes. A multi-page TIFF saved as TIFF remains a multi-page TIFF. A failed export leaves existing destination files intact.
5. **Export as images…** renders PDF pages at a fixed 200 DPI. PNG, JPEG, BMP and WebP produce numbered page files in a dedicated output folder; TIFF produces one multi-page file. The source PDF tab remains open with its current edits and pending-change state intact.

## Architecture and data contracts

- `document.py` owns the open document, pending redactions and pending rotations. PDF redaction rectangles are stored in unrotated PDF page coordinates as `(x0, y0, x1, y1)` point values, with a page index and style. Raster rectangles are stored in image pixel coordinates, with a frame/page index and style. Display coordinates are converted with the page rotation/derotation matrices or raster scale/rotation transform.
- `viewer.py` creates one lightweight widget per page, renders visible pages on demand and retains at most six rendered page images. It owns only view state (zoom, layout mode, current page, highlight rectangles).
- `window.py` owns menus, actions and dialogs. It saves only language and cover style in `QSettings`. `i18n.py` contains English/Polish strings; source identifiers and repository content remain English.
- `search.py` normalizes text for case/diacritic options and finds words or phrases within a line. It currently does not find phrases across line or page breaks.
- Pillow handles raster input and output for JPEG, PNG, TIFF, BMP and WebP, including multi-page TIFF. A raster document reports no searchable text, and the window disables the search field and related actions while it is active.

## Redaction and privacy behavior

- Use `Page.add_redact_annot()` and `Page.apply_redactions()` to remove intersecting text characters, overlapping image pixels and touched vector graphics. Raster save must rewrite the covered pixels into a new encoded image; it must not preserve the original pixels behind a reversible overlay. Black is the safest style for sensitive material. Blurred cover styles are derived from the source pixels and may retain visual clues about the covered content.
- Apply rotations and save with `garbage=4`, `clean=True`, `deflate=True`, without incremental updates. When redactions are present, remove common hidden data with `Document.scrub()`: metadata, attachments, scripts, links and form responses. A redaction save therefore removes those features when they existed in the original document.
- Raster save applies EXIF orientation to the pixels before encoding and strips source metadata, including EXIF, GPS, comments and embedded thumbnails. When writing a format without alpha support (for example JPEG), transparent pixels are composited against white. Build and validate the complete output before replacing the source. A format conversion may change encoding/compression characteristics; the original pixel dimensions are retained except when rotation changes orientation.
- Before PDF-to-image export, apply pending redactions and rotations to a temporary PDF copy and render that copy at 200 DPI. Never export the unredacted in-memory source when there are pending edits. Use numbered page filenames in a dedicated folder for single-page formats; encode TIFF pages into one multi-page TIFF. PDF export does not mark source edits as saved or change the active PDF path. Existing output files must not be replaced until export succeeds.
- Reopen the temporary PDF and reject it if the page count differs or extractable text characters intersect a selected rectangle. This is a bounded verification, not a proof that arbitrary PDF objects or duplicate secrets outside the selected areas do not exist.
- The source document remains untouched until Save intentionally replaces it. Save as writes a separate destination. There is no network processing or telemetry.

## UI and visual system

Use native Qt widgets with a restrained Windows-style palette: light surfaces `#ffffff/#f3f5f8`, dark surfaces `#171b22/#222832`, blue `#2d77bf` for active controls, and a single 24 px stroke-icon family. All controls have text or tooltips. The top menu has File and Settings; the search field sits at the right, following the supplied screenshot's field, arrows and option menu. The editing toolbar can be hidden. The bottom bar centers page navigation and places page mode and zoom on the right. The two requested page-mode icons currently mean single and continuous; facing modes are deferred until their behavior is implemented.

The operating-system color scheme is read when the window opens and updated when Windows reports a theme change. The application and installer use the transparent program icon based on the supplied draft.

## Packaging and licensing

Python 3.11+, PySide6, PyMuPDF and Pillow. PyInstaller builds a Windows app directory; Inno Setup packages it into one installer and adds Open with registrations for PDF, JPEG/JPG, PNG, TIFF, BMP and WebP without changing the user's default viewer. Source and distribution use AGPL-3.0-only to match the open-source route for PyMuPDF. Before public release, perform a dependency notice and installer verification pass.

## Verification and remaining work

Automated checks should create synthetic PDF and raster fixtures. Cover format opening and conversion for JPEG, PNG, multi-page TIFF, BMP and WebP; verify EXIF orientation and metadata removal; verify alpha handling; confirm redacted pixels do not remain recoverable; and check search is disabled for raster tabs while PDF search remains available. Check PDF export at 200 DPI, numbered multi-page outputs, and multi-page TIFF output, including pending redactions and rotations. Manual checks should cover drawing, all cover styles, multiple pages, Polish and English, light and dark Windows modes, password handling, zoom fit, installer Open with registration, and reopening outputs in independent viewers. Further PDF security tests need scanned images, reused image objects, layered/vector PDFs, forms, signatures, annotations and malformed files. A large-file performance pass and accessible keyboard workflow are also pending.
