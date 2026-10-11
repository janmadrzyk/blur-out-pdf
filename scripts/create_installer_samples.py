"""Create harmless files for checking Windows Open with registrations."""

from pathlib import Path
import sys

import pymupdf
from PIL import Image, ImageDraw


def main() -> None:
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 80), "SYNTHETIC INSTALLER TEST", fontsize=18)
        pdf.save(destination / "sample.pdf")

    image = Image.new("RGB", (400, 180), "white")
    ImageDraw.Draw(image).text((20, 70), "SYNTHETIC INSTALLER TEST", fill="black")
    for extension, format_name in (
        ("jpg", "JPEG"), ("jpeg", "JPEG"), ("png", "PNG"),
        ("tif", "TIFF"), ("tiff", "TIFF"), ("bmp", "BMP"),
        ("webp", "WEBP"),
    ):
        image.save(destination / f"sample.{extension}", format=format_name)


if __name__ == "__main__":
    main()
