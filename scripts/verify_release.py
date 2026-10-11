"""Check a Windows release candidate and write its SHA-256 checksum.

The checks cover the built one-directory payload and the installer's source
declarations. They do not replace an installation test on a clean machine.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import re
import sys


PROJECT = Path(__file__).resolve().parents[1]
SUPPORTED_SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")
LICENSE_FILES = ("GPL-3.0.txt", "LGPL-3.0.txt", "Python-LICENSE.txt", "Pillow-LICENSE.txt")


def _read_pe_product_version(path: Path) -> str:
    """Read ProductVersion from Windows PE string resources."""
    version = ctypes.WinDLL("version", use_last_error=True)
    version.GetFileVersionInfoSizeW.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD))
    version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    size = version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise ValueError(f"Missing Windows version resource: {path}")
    data = ctypes.create_string_buffer(size)
    version.GetFileVersionInfoW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p)
    version.GetFileVersionInfoW.restype = wintypes.BOOL
    if not version.GetFileVersionInfoW(str(path), 0, size, data):
        raise ValueError(f"Cannot read Windows version resource: {path}")
    version.VerQueryValueW.argtypes = (
        ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)
    )
    version.VerQueryValueW.restype = wintypes.BOOL

    pointer = ctypes.c_void_p()
    length = wintypes.UINT()
    if not version.VerQueryValueW(data, r"\VarFileInfo\Translation", ctypes.byref(pointer), ctypes.byref(length)):
        raise ValueError(f"Missing version translation: {path}")
    if length.value < 4:
        raise ValueError(f"Invalid version translation: {path}")
    translation = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_ushort))
    language, code_page = translation[0], translation[1]
    key = f"\\StringFileInfo\\{language:04X}{code_page:04X}\\ProductVersion"
    if not version.VerQueryValueW(data, key, ctypes.byref(pointer), ctypes.byref(length)):
        raise ValueError(f"Missing ProductVersion: {path}")
    return ctypes.wstring_at(pointer, length.value).rstrip("\0").strip()


def _has_icon_resource(path: Path) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LoadLibraryExW.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMODULE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ssize_t)
    kernel32.EnumResourceNamesW.argtypes = (wintypes.HMODULE, ctypes.c_void_p, callback_type, ctypes.c_ssize_t)
    kernel32.EnumResourceNamesW.restype = wintypes.BOOL
    kernel32.FreeLibrary.argtypes = (wintypes.HMODULE,)
    kernel32.FreeLibrary.restype = wintypes.BOOL
    module = kernel32.LoadLibraryExW(str(path), None, 0x00000002)
    if not module:
        raise ValueError(f"Cannot inspect Windows icon resource: {path}")
    try:
        # RT_GROUP_ICON = 14. A non-empty group exists only when an icon is embedded.
        found = False

        @callback_type
        def capture(_module, _kind, _name, _context):
            nonlocal found
            found = True
            return False

        kernel32.EnumResourceNamesW(module, ctypes.c_void_p(14), capture, 0)
        return found
    finally:
        kernel32.FreeLibrary(module)


def _check_installer_source(source: str) -> None:
    required = (
        r"SetupIconFile=app.ico",
        r'Source: "..\dist\BlurOutPDF\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion',
        r"ChangesAssociations=yes",
        r"BlurOutPDF.PDF\shell\open\command",
        r"BlurOutPDF.Raster\shell\open\command",
    )
    for declaration in required:
        if declaration not in source:
            raise ValueError(f"Installer declaration missing: {declaration}")
    for suffix in SUPPORTED_SUFFIXES:
        if not re.search(rf'ValueName: "{re.escape(suffix)}";', source):
            raise ValueError(f"Installer Open with integration missing: {suffix}")


def verify_release(project: Path = PROJECT, version: str | None = None) -> Path:
    if sys.platform != "win32":
        raise ValueError("Release resource verification requires Windows")
    if version is None:
        sys.path.insert(0, str(project / "src"))
        from blurout_pdf import __version__

        version = __version__
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Invalid release version: {version}")
    bundle = project / "dist" / "BlurOutPDF"
    app = bundle / "BlurOutPDF.exe"
    installer = project / "dist" / f"BlurOutPDF-Setup-{version}.exe"
    for path in (app, installer, bundle / "LICENSE", bundle / "THIRD_PARTY_NOTICES.md", project / "packaging" / "app.ico"):
        if not path.is_file():
            raise ValueError(f"Release file missing: {path}")
    for name in LICENSE_FILES:
        path = bundle / "licenses" / name
        if not path.is_file():
            raise ValueError(f"License text missing: {path}")
    for path in (app, installer):
        actual = _read_pe_product_version(path)
        if actual != version:
            raise ValueError(f"ProductVersion mismatch in {path.name}: {actual} != {version}")
        if not _has_icon_resource(path):
            raise ValueError(f"Application icon missing in {path.name}")

    internal = bundle / "_internal"
    if not internal.is_dir() or not (internal / "blurout_pdf" / "assets" / "app.png").is_file():
        raise ValueError("Application artwork missing from bundle")
    artwork = internal / "blurout_pdf" / "assets" / "app.png"
    forbidden = []
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = (part.lower() for part in path.relative_to(bundle).parts)
        if (
            (path.suffix.lower() in (*SUPPORTED_SUFFIXES, ".traineddata") and path != artwork)
            or any(part in ("tests", "fixtures", "private") for part in relative_parts)
            or "virtualkeyboard" in path.name.lower()
            or (path.parent == internal and path.name.lower().startswith("icu") and path.suffix.lower() == ".dll")
        ):
            forbidden.append(path)
    if forbidden:
        raise ValueError(f"Unexpected release payload: {forbidden}")
    _check_installer_source((project / "packaging" / "windows.iss").read_text(encoding="utf-8-sig"))

    digest = hashlib.sha256()
    with installer.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum = project / "dist" / "SHA256.txt"
    checksum.write_text(f"{digest.hexdigest().upper()}  {installer.name}\n", encoding="ascii")
    return checksum


if __name__ == "__main__":
    try:
        output = verify_release()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Release payload and declarations verified; checksum: {output}")
