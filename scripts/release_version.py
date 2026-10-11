"""Generate Windows executable metadata from the package version."""

from pathlib import Path
import re
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from blurout_pdf import __version__  # noqa: E402


def main() -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", __version__):
        raise SystemExit(f"Windows release requires major.minor.patch: {__version__}")
    version_parts = tuple(int(part) for part in __version__.split(".")) + (0,)
    destination = PROJECT / "build" / "version_info.txt"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(filevers={parts}, prodvers={parts}, mask=0x3f, flags=0x0, "
        "OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[StringFileInfo([StringTable('040904B0', [\n"
        "    StringStruct('CompanyName', 'BlurOut PDF'),\n"
        "    StringStruct('FileDescription', 'BlurOut PDF'),\n"
        "    StringStruct('FileVersion', '{version}'),\n"
        "    StringStruct('InternalName', 'BlurOutPDF'),\n"
        "    StringStruct('OriginalFilename', 'BlurOutPDF.exe'),\n"
        "    StringStruct('ProductName', 'BlurOut PDF'),\n"
        "    StringStruct('ProductVersion', '{version}')\n"
        "  ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n".format(
            parts=version_parts, version=__version__
        ),
        encoding="utf-8",
    )
    print(__version__)


if __name__ == "__main__":
    main()
