from pathlib import Path

import pymupdf

from rectveil.document import PdfDocument


def make_pdf(path: Path) -> None:
    pdf = pymupdf.open()
    page = pdf.new_page(width=400, height=300)
    page.insert_text((40, 70), "PUBLIC SECRET PUBLIC", fontsize=18)
    pdf.set_metadata({"title": "SECRET metadata"})
    pdf.embfile_add("secret.txt", b"SECRET attachment")
    pdf.save(path)
    pdf.close()


def test_redaction_removes_text_and_hidden_data(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    result = tmp_path / "result.pdf"
    make_pdf(source)
    document = PdfDocument()
    assert document.open(source)
    secret = document.page(0).search_for("SECRET")[0]
    document.add_redaction(0, secret + (-1, -1, 1, 1), "black")
    document.save(result)
    with pymupdf.open(result) as pdf:
        assert "SECRET" not in pdf[0].get_text()
        assert "PUBLIC" in pdf[0].get_text()
        assert pdf.embfile_count() == 0
        assert "SECRET" not in str(pdf.metadata)
        assert pdf[0].get_pixmap().samples


def test_rotation_and_grain_survive_save(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    result = tmp_path / "result.pdf"
    make_pdf(source)
    document = PdfDocument()
    document.open(source)
    document.rotate(0, 90)
    assert document.display_size(0) == (300, 400)
    secret = document.page_to_display(0, document.page(0).search_for("SECRET")[0])
    document.add_redaction(0, secret + (-2, -2, 2, 2), "fine")
    document.save(result)
    with pymupdf.open(result) as pdf:
        assert pdf[0].rotation == 90
        assert "SECRET" not in pdf[0].get_text()
        assert pdf[0].get_images(full=True)


def test_redaction_then_pending_rotation_removes_text_before_rotating(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    result = tmp_path / "result.pdf"
    make_pdf(source)
    document = PdfDocument()
    document.open(source)
    secret = document.page(0).search_for("SECRET")[0]
    document.add_redaction(0, secret + (-2, -2, 2, 2), "black")
    document.rotate(0, 90)
    document.save(result)
    with pymupdf.open(result) as pdf:
        assert pdf[0].rotation == 90
        assert "SECRET" not in pdf[0].get_text()


def test_blur_preview_changes_with_underlying_page_content(tmp_path: Path) -> None:
    previews = []
    for index, text in enumerate(("ALPHA", "OMEGA")):
        source = tmp_path / f"source-{index}.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=400, height=300)
            page.insert_text((40, 70), text, fontsize=18)
            pdf.save(source)
        document = PdfDocument()
        document.open(source)
        document.add_redaction(0, pymupdf.Rect(35, 45, 160, 85), "fine")
        previews.append(document.redactions[0].visual_data)
        document.close()
    assert previews[0] and previews[1]
    assert previews[0] != previews[1]


def test_save_to_same_path_is_full_replacement(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source)
    document = PdfDocument()
    document.open(source)
    secret = document.page(0).search_for("SECRET")[0]
    document.add_redaction(0, secret, "black")
    document.save(source)
    assert not document.dirty
    with pymupdf.open(source) as pdf:
        assert "SECRET" not in pdf[0].get_text()


def test_redaction_removes_scanned_image_pixels(tmp_path: Path) -> None:
    source = tmp_path / "image.pdf"
    result = tmp_path / "redacted.pdf"
    image = pymupdf.Pixmap(pymupdf.csRGB, 20, 20, bytes((20, 80, 220)) * 400, False)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=200, height=200)
        page.insert_image(pymupdf.Rect(40, 40, 140, 140), stream=image.tobytes("png"))
        pdf.save(source)
    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, pymupdf.Rect(65, 65, 115, 115), "black")
    document.save(result)
    with pymupdf.open(result) as pdf:
        pix = pdf[0].get_pixmap()
        assert pix.pixel(90, 90)[:3] == (0, 0, 0)
        assert pix.pixel(50, 50)[:3] == (20, 80, 220)


def test_undo_last_pending_redaction(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source)
    document = PdfDocument()
    document.open(source)
    document.add_redaction(0, document.page(0).search_for("SECRET")[0], "black")
    assert document.dirty
    assert document.undo_last_redaction() == 0
    assert not document.dirty
