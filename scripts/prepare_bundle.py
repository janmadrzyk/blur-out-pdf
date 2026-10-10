"""Add release notices and remove unused Qt modules from a PyInstaller bundle."""

from pathlib import Path
import shutil


PROJECT = Path(__file__).resolve().parents[1]
BUNDLE = PROJECT / "dist" / "BlurOutPDF"
INTERNAL = BUNDLE / "_internal"
LICENSE_FILES = (
    "GPL-3.0.txt",
    "LGPL-3.0.txt",
    "Python-LICENSE.txt",
    "Pillow-LICENSE.txt",
)


def main() -> None:
    if not (BUNDLE / "BlurOutPDF.exe").is_file() or not INTERNAL.is_dir():
        raise SystemExit("Build the PyInstaller one-directory bundle first")

    # QtVirtualKeyboard is pulled in by the Qt platform-input-context hook,
    # although this widget application does not use it. Qt lists this module
    # as GPL-only; leaving it in the installer would broaden its license scope.
    for relative in (
        "PySide6/Qt6VirtualKeyboard.dll",
        "PySide6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll",
    ):
        target = INTERNAL / relative
        if target.is_file():
            target.unlink()

    for source in (PROJECT / "LICENSE", PROJECT / "THIRD_PARTY_NOTICES.md"):
        if not source.is_file():
            raise SystemExit(f"Missing notice: {source}")
        shutil.copy2(source, BUNDLE / source.name)

    destination = BUNDLE / "licenses"
    destination.mkdir(exist_ok=True)
    for name in LICENSE_FILES:
        source = PROJECT / "licenses" / name
        if not source.is_file():
            raise SystemExit(f"Missing license text: {source}")
        shutil.copy2(source, destination / name)

    forbidden = [
        path for path in BUNDLE.rglob("*")
        if path.is_file() and (
            path.suffix.lower() == ".traineddata"
            or "virtualkeyboard" in path.name.lower()
        )
    ]
    if forbidden:
        raise SystemExit(f"Unexpected bundled files: {forbidden}")
    print("Bundle notices present; no OCR models or Qt Virtual Keyboard")


if __name__ == "__main__":
    main()
