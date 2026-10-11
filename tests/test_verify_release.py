"""Synthetic checks for release payload validation."""

import hashlib
from pathlib import Path

import pytest

from scripts import verify_release


@pytest.fixture
def candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bundle = tmp_path / "dist" / "BlurOutPDF"
    (bundle / "licenses").mkdir(parents=True)
    (bundle / "_internal" / "blurout_pdf" / "assets").mkdir(parents=True)
    (tmp_path / "packaging").mkdir()
    (bundle / "BlurOutPDF.exe").write_bytes(b"app")
    (bundle / "LICENSE").write_text("license")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text("notices")
    (bundle / "_internal" / "blurout_pdf" / "assets" / "app.png").write_bytes(b"icon")
    for name in verify_release.LICENSE_FILES:
        (bundle / "licenses" / name).write_text(name)
    (tmp_path / "packaging" / "app.ico").write_bytes(b"icon")
    (tmp_path / "dist" / "BlurOutPDF-Setup-1.0.0.exe").write_bytes(b"setup")
    (tmp_path / "packaging" / "windows.iss").write_text(
        'SetupIconFile=app.ico\nChangesAssociations=yes\n'
        'Source: "..\\dist\\BlurOutPDF\\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion\n'
        'BlurOutPDF.PDF\\shell\\open\\command\n'
        'BlurOutPDF.Raster\\shell\\open\\command\n'
        + "".join(f'ValueName: "{suffix}";\n' for suffix in verify_release.SUPPORTED_SUFFIXES),
        encoding="utf-8",
    )
    monkeypatch.setattr(verify_release, "_read_pe_product_version", lambda path: "1.0.0")
    monkeypatch.setattr(verify_release, "_has_icon_resource", lambda path: True)
    monkeypatch.setattr(verify_release.sys, "platform", "win32")
    return tmp_path


def test_candidate_checksum(candidate: Path) -> None:
    checksum = verify_release.verify_release(candidate, "1.0.0")
    expected = hashlib.sha256(b"setup").hexdigest().upper()
    assert checksum.read_text(encoding="ascii") == f"{expected}  BlurOutPDF-Setup-1.0.0.exe\n"


def test_rejects_missing_notice(candidate: Path) -> None:
    (candidate / "dist" / "BlurOutPDF" / "LICENSE").unlink()
    with pytest.raises(ValueError, match="Release file missing"):
        verify_release.verify_release(candidate, "1.0.0")


def test_rejects_private_fixture(candidate: Path) -> None:
    (candidate / "dist" / "BlurOutPDF" / "_internal" / "private.pdf").write_bytes(b"private")
    with pytest.raises(ValueError, match="Unexpected release payload"):
        verify_release.verify_release(candidate, "1.0.0")


def test_rejects_missing_open_with_type(candidate: Path) -> None:
    script = candidate / "packaging" / "windows.iss"
    script.write_text(script.read_text(encoding="utf-8").replace('ValueName: ".webp";', ""), encoding="utf-8")
    with pytest.raises(ValueError, match="Open with integration missing: .webp"):
        verify_release.verify_release(candidate, "1.0.0")


def test_rejects_mismatched_version(candidate: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify_release, "_read_pe_product_version", lambda path: "0.9.0")
    with pytest.raises(ValueError, match="ProductVersion mismatch"):
        verify_release.verify_release(candidate, "1.0.0")
