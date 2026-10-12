# Changelog

## 1.0.0 — release candidate

This version is being prepared for its first public release. The source repository is public; the release tag and installer have not yet been published.

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

### Still to complete before the first software release

- Complete the installer lifecycle checks, including fresh install, same-version behavior, running-app handling and uninstall (Issue 4).
- Accept the exact CI candidate in a clean Windows environment and complete the application checks (Issues 5–6).
- Tag `v1.0.0` and publish the accepted installer with its verified checksum (Issue 7).
