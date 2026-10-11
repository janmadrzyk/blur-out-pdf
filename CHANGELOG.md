# Changelog

## 1.0.0 — release candidate

This version is being prepared for its first public release. The release tag and installer have not yet been published.

### Included

- PDF and common raster image viewing, multiple tabs, zoom and page navigation.
- Permanent rectangular redaction on saved PDF and raster output, with black and blurred cover styles. Blurred covers may retain visual clues.
- PDF text search and optional scanned-page OCR when compatible local language data exists.
- PDF page image export, raster format conversion, page rotation and PDF metadata editing.
- Polish and English interface, light and dark appearance, and an About dialog with the version, license and future project URL.
- Windows packaging that includes third-party notices and license texts without OCR models.

### Known limitations

- OCR is optional and may be unavailable on a clean Windows installation.
- PDFs with complex interactive features or malformed structure need extra review before sensitive disclosure. Inspect every saved result independently.
- The GitHub project URL in About will resolve after the repository is published.

### Still to complete before publication

- Installer upgrade, repeat-install, downgrade and uninstall checks (Issue 4).
- Reproducible release-candidate build and clean Windows acceptance pass (Issues 5–6).
- Public repository and GitHub Release with verified checksum (Issue 7).
