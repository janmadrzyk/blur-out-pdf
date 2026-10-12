# Changelog

## 1.0.1 — release candidate

This candidate supersedes the unpublished 1.0.0 candidate. The patch version allows existing 1.0.0 test installations to upgrade through the installer version gate. No 1.0.0 software release was published.

### Changes prepared for verification

- Restore the Windows **Open with** option for PDFs and supported raster formats.
- Show the dragged selection marquee in the document and image file picker.

Automated and manual verification of these changes is tracked in [the release checklist](docs/ISSUES.md). Clean-Windows installer checks, including upgrade from the 1.0.0 candidate and uninstall cleanup, must be repeated on the exact 1.0.1 CI artifact. Publish `v1.0.1` only after that artifact and its checksum are accepted.

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

### Acceptance work carried forward to 1.0.1

- Complete the installer lifecycle checks, including fresh install, same-version behavior, running-app handling and uninstall (Issue 4).
- Accept the exact CI candidate in a clean Windows environment and complete the application checks (Issues 5–6).
- Tag the accepted current candidate and publish its installer with the verified checksum (Issue 7); the current target is `v1.0.1`.
