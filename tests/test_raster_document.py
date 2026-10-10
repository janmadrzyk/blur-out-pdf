"""End-to-end raster conversion with synthetic content only."""

from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from PySide6.QtGui import QImage

PIL = pytest.importorskip("PIL")
from PIL import Image, PngImagePlugin

from blurout_pdf.document import PdfDocument


def test_png_redaction_replaces_pixels_and_discards_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    target = tmp_path / "result.png"
    details = PngImagePlugin.PngInfo()
    details.add_text("Comment", "SECRET comment")
    Image.new("RGB", (40, 30), (235, 15, 20)).save(source, pnginfo=details)

    document = PdfDocument()
    assert document.open(source)
    assert document.is_raster
    assert document.page_count == 1
    document.add_redaction(0, pymupdf.Rect(10, 8, 25, 22), "black")
    assert document.save(target) == [target]
    assert document.path == target
    assert not document.dirty

    with Image.open(target) as saved:
        assert saved.size == (40, 30)
        assert saved.getpixel((15, 12)) == (0, 0, 0)
        assert saved.getpixel((2, 2)) == (235, 15, 20)
        assert "Comment" not in saved.info
    assert b"SECRET comment" not in target.read_bytes()


def test_transparency_and_rotation_survive_png_save(tmp_path: Path) -> None:
    source = tmp_path / "transparent.png"
    target = tmp_path / "turned.png"
    image = Image.new("RGBA", (20, 10), (0, 0, 0, 0))
    image.putpixel((1, 1), (20, 100, 220, 255))
    image.save(source)
    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(8, 2, 16, 8), "black")
    document.rotate(0, 90)
    document.save(target)
    with Image.open(target) as saved:
        assert saved.size == (10, 20)
        assert saved.mode == "RGBA"
        assert saved.getpixel((8, 1)) == (20, 100, 220, 255)
        assert saved.getpixel((5, 10)) == (0, 0, 0, 255)
        assert saved.getpixel((0, 0))[3] == 0


def test_jpeg_exif_orientation_is_applied_and_exif_is_dropped(tmp_path: Path) -> None:
    source = tmp_path / "camera.jpg"
    target = tmp_path / "upright.png"
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise for display.
    exif[315] = "SECRET photographer"
    Image.new("RGB", (10, 20), "blue").save(source, exif=exif)
    document = PdfDocument()
    document.open(source)
    assert document.display_size(0) == (20, 10)
    document.save(target)
    with Image.open(target) as saved:
        assert saved.size == (20, 10)
        assert not saved.getexif()
    assert b"SECRET photographer" not in target.read_bytes()


def test_multipage_tiff_save_and_conversion(tmp_path: Path) -> None:
    source = tmp_path / "scans.tiff"
    tiff = tmp_path / "redacted.tiff"
    png = tmp_path / "converted.png"
    first = Image.new("RGB", (30, 20), (200, 10, 10))
    second = Image.new("RGB", (30, 20), (10, 10, 200))
    first.save(source, save_all=True, append_images=[second])
    document = PdfDocument()
    document.open(source)
    assert document.page_count == 2
    document.add_redaction(1, pymupdf.Rect(5, 5, 15, 15), "black")
    assert document.save(tiff) == [tiff]
    with Image.open(tiff) as saved:
        assert saved.n_frames == 2
        saved.seek(1)
        assert saved.getpixel((10, 10)) == (0, 0, 0)
    outputs = document.save(png)
    assert outputs == [tmp_path / "converted" / "converted-0001.png",
                       tmp_path / "converted" / "converted-0002.png"]
    assert document.path == tiff
    assert Image.open(outputs[0]).getpixel((0, 0)) == (200, 10, 10)


def test_pdf_export_renders_redactions_without_changing_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    target = tmp_path / "pages.png"
    with pymupdf.open() as pdf:
        for word in ("SECRET", "PUBLIC"):
            page = pdf.new_page(width=144, height=72)
            page.insert_text((20, 35), word, fontsize=20)
        pdf.save(source)
    document = PdfDocument()
    document.open(source)
    secret = document.page(0).search_for("SECRET")[0]
    document.add_redaction(0, secret, "black")
    outputs = document.export_images(target)
    assert outputs == [tmp_path / "pages" / "pages-0001.png",
                       tmp_path / "pages" / "pages-0002.png"]
    assert document.path == source
    assert document.dirty
    with Image.open(outputs[0]) as exported:
        assert exported.size == (400, 200)
        # Center of the former word is dark after redaction.
        center = (round((secret.x0 + secret.x1) / 2 * 200 / 72),
                  round((secret.y0 + secret.y1) / 2 * 200 / 72))
        assert exported.convert("RGB").getpixel(center) == (0, 0, 0)
    with pymupdf.open(source) as pdf:
        assert "SECRET" in pdf[0].get_text()


def test_animated_webp_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "animated.webp"
    first = Image.new("RGB", (12, 12), "red")
    second = Image.new("RGB", (12, 12), "blue")
    first.save(source, save_all=True, append_images=[second], duration=100, loop=0)
    document = PdfDocument()
    with pytest.raises(ValueError, match="Animated"):
        document.open(source)


@pytest.mark.parametrize("suffix", [".jpg", ".bmp", ".webp", ".tif"])
def test_single_image_format_conversion_keeps_redaction_and_drops_metadata(
    tmp_path: Path, suffix: str,
) -> None:
    source = tmp_path / "source.png"
    target = tmp_path / f"output{suffix}"
    details = PngImagePlugin.PngInfo()
    details.add_text("Comment", "PRIVATE-NOTE-123")
    Image.new("RGB", (80, 60), "white").save(source, pnginfo=details)

    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(15, 10, 65, 50), "black")
    assert document.save(target) == [target]
    assert document.path == target

    with Image.open(target) as result:
        assert result.size == (80, 60)
        assert max(result.convert("RGB").getpixel((40, 30))) < 10
        assert "Comment" not in result.info
    assert b"PRIVATE-NOTE-123" not in target.read_bytes()


def test_blurred_raster_save_rewrites_pixels(tmp_path: Path) -> None:
    source = tmp_path / "pattern.png"
    target = tmp_path / "blurred.png"
    image = Image.new("RGB", (80, 60), "white")
    for x in range(10, 70, 2):
        for y in range(10, 50):
            image.putpixel((x, y), (0, 0, 0))
    image.save(source)

    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(10, 10, 70, 50), "fine")
    document.save(target)
    with Image.open(target) as result:
        assert result.getpixel((2, 2)) == image.getpixel((2, 2))
        assert result.crop((10, 10, 70, 50)).tobytes() != image.crop((10, 10, 70, 50)).tobytes()


def test_pdf_export_to_multipage_tiff(tmp_path: Path) -> None:
    source = tmp_path / "two-pages.pdf"
    target = tmp_path / "two-pages.tiff"
    with pymupdf.open() as pdf:
        pdf.new_page(width=72, height=72)
        pdf.new_page(width=144, height=72)
        pdf.save(source)
    document = PdfDocument()
    document.open(source)

    assert document.export_images(target) == [target]
    with Image.open(target) as result:
        assert result.n_frames == 2
        assert result.size == (200, 200)
        result.seek(1)
        assert result.size == (400, 200)


def test_large_raster_blur_stays_bounded_and_can_be_saved(tmp_path: Path) -> None:
    source = tmp_path / "large.png"
    target = tmp_path / "large-redacted.png"
    Image.new("RGB", (3500, 3500), "white").save(source)
    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(0, 0, 3500, 3500), "fine")

    preview = document.redactions[0].visual_data
    assert preview is not None
    assert not QImage.fromData(preview, "PNG").isNull()
    with Image.open(BytesIO(preview)) as decoded:
        assert max(decoded.size) <= 1536
        sample = decoded.convert("RGB")
        assert len({sample.getpixel((x, y))
                    for x in range(0, decoded.width, 100)
                    for y in range(0, decoded.height, 100)}) > 1
    document.save(target)
    with Image.open(target) as saved:
        assert saved.size == (3500, 3500)


def test_overlapping_raster_blur_uses_previous_redaction(tmp_path: Path) -> None:
    source = tmp_path / "white.png"
    Image.new("RGB", (160, 160), "white").save(source)
    layered = PdfDocument()
    layered.open(source)
    layered.add_redaction(0, pymupdf.Rect(10, 10, 100, 100), "black")
    layered.add_redaction(0, pymupdf.Rect(50, 50, 150, 150), "fine")
    layered_visual = layered.redactions[1].visual_data
    layered.undo()
    layered.redo()
    assert layered.redactions[1].visual_data == layered_visual
    plain = PdfDocument()
    plain.open(source)
    plain.add_redaction(0, pymupdf.Rect(50, 50, 150, 150), "fine")

    with Image.open(BytesIO(layered.redactions[1].visual_data)) as after_black:
        with Image.open(BytesIO(plain.redactions[0].visual_data)) as without_black:
            # Both use the same grain seed. The darker pixel can only come from
            # the earlier black rectangle under the second blur.
            assert sum(after_black.convert("RGB").getpixel((20, 20))) < sum(
                without_black.convert("RGB").getpixel((20, 20)))
            expected = after_black.convert("RGB").getpixel((20, 20))
    layered.save(tmp_path / "layered.png")
    with Image.open(tmp_path / "layered.png") as saved:
        assert saved.convert("RGB").getpixel((70, 70)) == expected

    saved_first = PdfDocument()
    saved_first.open(source)
    saved_first.add_redaction(0, pymupdf.Rect(10, 10, 100, 100), "black")
    saved_first.save(tmp_path / "first-pass.png")
    saved_first.add_redaction(0, pymupdf.Rect(50, 50, 150, 150), "fine")
    with Image.open(BytesIO(saved_first.redactions[0].visual_data)) as after_save:
        with Image.open(BytesIO(plain.redactions[0].visual_data)) as without_black:
            assert sum(after_save.convert("RGB").getpixel((20, 20))) < sum(
                without_black.convert("RGB").getpixel((20, 20)))


def test_resizing_earlier_redaction_refreshes_only_affected_later_blurs(tmp_path: Path) -> None:
    source = tmp_path / "white.png"
    Image.new("RGB", (200, 200), "white").save(source)
    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(10, 10, 40, 40), "black")
    document.add_redaction(0, pymupdf.Rect(30, 30, 90, 90), "fine")
    document.add_redaction(0, pymupdf.Rect(120, 120, 180, 180), "fine")
    document.add_redaction(0, pymupdf.Rect(80, 80, 130, 130), "coarse")
    old_visuals = [item.visual_data for item in document.redactions]

    old_area = pymupdf.Rect(document.redactions[0].rect)
    new_area = pymupdf.Rect(10, 10, 70, 70)
    document.update_redaction(0, new_area, refresh_visual=False)
    document.refresh_redaction_visuals(0, 0, changed_area=old_area | new_area)

    assert document.redactions[1].visual_data is not old_visuals[1]
    assert document.redactions[2].visual_data is old_visuals[2]
    assert document.redactions[3].visual_data is not old_visuals[3]
