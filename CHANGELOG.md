# Changelog

## 1.0.1 — 2026-10-12

The first public release. It supersedes the unpublished 1.0.0 candidate. The patch version allows existing 1.0.0 test installations to upgrade through the installer version gate.

### Changes

- Restore the Windows **Open with** option for PDFs and supported raster formats.
- Show the dragged selection marquee in the document and image file picker.

The installer is unsigned, so Windows may show a SmartScreen warning that the publisher is unknown. Verify the installer against the published SHA-256 checksum before running it. See the [release notes](docs/RELEASE_NOTES_1.0.1.md) for details.

## 1.0.0 — release candidate

This earlier candidate was not publicly released and is superseded by 1.0.1. The source repository is public; no 1.0.0 release tag or installer release was published.

### Included

- PDF and common raster image viewing, multiple tabs, zoom and page navigation.
- Permanent rectangular redaction on saved PDF and raster output, with black and blurred cover styles. Blurred covers may retain visual clues.
- PDF text search and optional scanned-page OCR when compatible local language data exists.
- PDF page image export, raster format conversion, page rotation and PDF metadata editing.
- Polish and English interface, light and dark appearance, and an About dialog with the version, license and project URL.
- Windows packaging that includes third-party notices and license texts without OCR models.

### Known limitations

- OCR is optional and may be unavailable on a clean Windows installation.
- PDFs with complex interactive features or malformed structure need extra review before sensitive disclosure. Inspect every saved result independently.
- The public GitHub repository is available at [janmadrzyk/blur-out-pdf](https://github.com/janmadrzyk/blur-out-pdf).

The acceptance work originally planned for this candidate was completed for the 1.0.1 release.
