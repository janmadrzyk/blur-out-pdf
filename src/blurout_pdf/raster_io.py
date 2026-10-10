"""Raster input and output. Saved files contain freshly encoded pixels only."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageOps


RASTER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"})
TIFF_EXTENSIONS = frozenset({".tif", ".tiff"})


def _pixel_copy(frame: Image.Image) -> Image.Image:
    """Apply EXIF orientation and discard metadata from each frame."""
    upright = ImageOps.exif_transpose(frame)
    mode = "RGBA" if "A" in upright.getbands() or "transparency" in upright.info else "RGB"
    converted = upright.convert(mode)
    return Image.frombytes(mode, converted.size, converted.tobytes())


def read_raster(path: Path) -> list[Image.Image]:
    if path.suffix.lower() not in RASTER_EXTENSIONS:
        raise ValueError("Unsupported image format")
    with Image.open(path) as source:
        expected = {
            ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
            ".tif": "TIFF", ".tiff": "TIFF", ".bmp": "BMP", ".webp": "WEBP",
        }[path.suffix.lower()]
        if source.format != expected:
            raise ValueError("Image content does not match its file extension")
        count = getattr(source, "n_frames", 1)
        if count > 1 and path.suffix.lower() not in TIFF_EXTENSIONS:
            raise ValueError("Animated images are not supported")
        pages = []
        for index in range(count):
            source.seek(index)
            pages.append(_pixel_copy(source))
        return pages


def png_bytes(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _for_format(image: Image.Image, extension: str) -> Image.Image:
    # JPEG and BMP cannot represent transparency. Composite on white rather
    # than silently replacing transparent pixels with black.
    if extension in {".jpg", ".jpeg", ".bmp"} and image.mode == "RGBA":
        opaque = Image.new("RGB", image.size, "white")
        opaque.paste(image, mask=image.getchannel("A"))
        return opaque
    return image


def _encode(path: Path, images: list[Image.Image], extension: str) -> None:
    format_name = {
        ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
        ".tif": "TIFF", ".tiff": "TIFF", ".bmp": "BMP", ".webp": "WEBP",
    }[extension]
    pages = [_for_format(image, extension) for image in images]
    options: dict[str, object] = {}
    if format_name == "JPEG":
        options["quality"] = 95
    if format_name == "TIFF" and len(pages) > 1:
        options["save_all"] = True
        options["append_images"] = pages[1:]
    pages[0].save(path, format=format_name, **options)


def _verify(path: Path, expected_pages: int, sizes: list[tuple[int, int]]) -> None:
    with Image.open(path) as saved:
        if getattr(saved, "n_frames", 1) != expected_pages:
            raise RuntimeError("Saved image has an unexpected page count")
        for index, size in enumerate(sizes):
            saved.seek(index)
            saved.load()
            if saved.size != size:
                raise RuntimeError("Saved image has unexpected dimensions")


def write_raster(target: str | Path, images: list[Image.Image]) -> list[Path]:
    """Write and verify image output before replacing a destination.

    Multi-page output to a single-page format is placed in a new folder named
    after the requested file stem. Existing folders are never overwritten.
    """
    if not images:
        raise ValueError("No image pages to save")
    destination = Path(target).resolve()
    extension = destination.suffix.lower()
    if extension not in RASTER_EXTENSIONS:
        raise ValueError("Unsupported image output format")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if len(images) > 1 and extension not in TIFF_EXTENSIONS:
        folder = destination.with_suffix("")
        if folder.exists():
            raise FileExistsError(f"Output folder already exists: {folder}")
        with tempfile.TemporaryDirectory(prefix="blurout-images-", dir=destination.parent) as temporary:
            staging = Path(temporary)
            names = [f"{destination.stem}-{index:04d}{extension}" for index in range(1, len(images) + 1)]
            for name, image in zip(names, images, strict=True):
                output = staging / name
                _encode(output, [image], extension)
                _verify(output, 1, [image.size])
            os.replace(staging, folder)
        return [folder / name for name in names]
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, prefix="blurout-image-", dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
        _encode(temporary, images, extension)
        _verify(temporary, len(images), [image.size for image in images])
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return [destination]
