"""Prevent installers with incomplete or destructive Open with registrations."""

from pathlib import Path

import pytest

from blurout_pdf.raster_io import RASTER_EXTENSIONS
from scripts import verify_release


SOURCE = (Path(__file__).resolve().parents[1] / "packaging" / "windows.iss").read_text(encoding="utf-8-sig")


def mutate_registration(subkey: str, old: str, new: str) -> str:
    lines = SOURCE.splitlines()
    for index, line in enumerate(lines):
        if f'Subkey: "{subkey}";' in line and old in line:
            lines[index] = line.replace(old, new)
            return "\n".join(lines)
    raise AssertionError(f"Registration not found: {subkey}")


def test_installer_registers_every_supported_format() -> None:
    assert set(verify_release.SUPPORTED_SUFFIXES) == {".pdf", *RASTER_EXTENSIONS}
    verify_release._check_installer_source(SOURCE)


@pytest.mark.parametrize("suffix", verify_release.SUPPORTED_SUFFIXES)
def test_key_without_named_progid_value_is_rejected(suffix: str) -> None:
    broken = mutate_registration(
        rf"Software\Classes\{suffix}\OpenWithProgids", "ValueType: string", "ValueType: none"
    )
    with pytest.raises(ValueError, match="registration invalid"):
        verify_release._check_installer_source(broken)


@pytest.mark.parametrize("suffix", verify_release.SUPPORTED_SUFFIXES)
def test_uninstall_must_remove_only_its_named_extension_value(suffix: str) -> None:
    broken = mutate_registration(
        rf"Software\Classes\{suffix}\OpenWithProgids", "uninsdeletevalue", "uninsdeletekey"
    )
    with pytest.raises(ValueError, match="uninstall cleanup missing"):
        verify_release._check_installer_source(broken)


@pytest.mark.parametrize("owner", ["BlurOutPDF.PDF", "BlurOutPDF.Raster", r"Applications\BlurOutPDF.exe"])
def test_open_command_quotes_executable_and_file_path(owner: str) -> None:
    broken = mutate_registration(
        rf"Software\Classes\{owner}\shell\open\command", '""%1""', "%1"
    )
    with pytest.raises(ValueError, match="registration invalid"):
        verify_release._check_installer_source(broken)


def test_application_needs_display_name_and_uninstall_cleanup() -> None:
    broken = mutate_registration(
        r"Software\Classes\Applications\BlurOutPDF.exe", 'ValueName: "FriendlyAppName"', 'ValueName: "Other"'
    )
    with pytest.raises(ValueError, match="integration missing: FriendlyAppName"):
        verify_release._check_installer_source(broken)
    broken = mutate_registration(
        r"Software\Classes\Applications\BlurOutPDF.exe", "uninsdeletekey", "uninsdeletevalue"
    )
    with pytest.raises(ValueError, match="uninstall cleanup missing"):
        verify_release._check_installer_source(broken)


def test_installer_must_leave_the_default_viewer_unchanged() -> None:
    broken = SOURCE.replace(
        "[Registry]", '[Registry]\nRoot: HKCU; Subkey: "Software\\Classes\\.pdf"; ValueType: string; ValueData: "BlurOutPDF.PDF";'
    )
    with pytest.raises(ValueError, match="preserve the default viewer"):
        verify_release._check_installer_source(broken)
