# Third-party inventory for the Windows package

Reviewed on 2026-10-10 against the project configuration, the existing local PyInstaller output, and installed package metadata. The version numbers below describe that local build environment; Issue 5 will control release versions and review the final candidate package.

| Component | Local version | Use and distribution | License / source |
| --- | --- | --- | --- |
| BlurOut PDF | 0.1.0 | Application source and installer | AGPL-3.0-only; root `LICENSE`. |
| CPython | 3.12.10 | Interpreter and standard library bundled by PyInstaller | Python Software Foundation license stack; [Python license](https://docs.python.org/3/license.html). |
| PyMuPDF and MuPDF | 1.28.2 | PDF rendering, editing and OCR integration | AGPL-3.0 or commercial; [PyMuPDF licensing](https://pymupdf.readthedocs.io/en/latest/about.html). The project uses the AGPL route. |
| PySide6 Essentials, Addons and Shiboken6 / Qt | 6.11.2 | Windows widgets, rendering and Qt plugins | LGPL-3.0-only or GPL alternatives; [Qt for Python](https://doc.qt.io/qtforpython-6/) and [Qt licensing](https://doc.qt.io/qt-6/licensing.html). Bundled dynamic libraries must remain replaceable; the app does not modify them. Some Qt modules have different licenses, so the release package must contain only needed modules. |
| Pillow | 12.3.0 | Raster input and output | MIT-CMU; [Pillow license](https://github.com/python-pillow/Pillow/blob/main/LICENSE). Its Windows wheel also contains native image codecs; review the exact wheel notices for the candidate build. |
| PyInstaller | 6.22.3 | Build tool; its bootloader is in the executable | GPL-2.0-or-later with bootloader exception; [PyInstaller license](https://pyinstaller.org/en/stable/license.html). |
| Inno Setup | Build tool | Creates the installer, but is not installed as an application component | [Inno Setup license](https://jrsoftware.org/isinfo.php). |
| pytest, setuptools and PyInstaller hook dependencies | Development only | Not intended as application runtime components | License files and metadata in their installed distributions; review again if build collection changes. |

The application icon and README screenshot are project assets; the screenshot uses a generated PDF. No external font asset is tracked. Windows system fonts are used by Qt. No Tesseract language data is tracked or intended to be installed.

The pre-audit PyInstaller output contained CPython, PyMuPDF, Pillow, PySide6/Shiboken6 and Qt libraries, but no license or notice files. It also contained `Qt6VirtualKeyboard.dll` and its input plugin, even though the app does not use them; Qt lists this module as GPL-only. `scripts/prepare_bundle.py` now removes those two unused files, copies `LICENSE`, `THIRD_PARTY_NOTICES.md` and the four texts in `licenses/` into the application directory, and rejects any `.traineddata` or remaining Virtual Keyboard file. The Inno Setup `[Files]` rule recursively includes this prepared directory. A fresh local PyInstaller build passed the preparation check on 2026-10-10.

The GPL and LGPL texts were taken from the [SPDX license list](https://github.com/spdx/license-list-data/tree/main/text); the Python license stack is from the [CPython 3.12.10 source tag](https://github.com/python/cpython/blob/v3.12.10/LICENSE); the Pillow license and native-code notices came from the installed 12.3.0 wheel. The final artifact must be inspected again in Issue 5 because dependency and Qt wheel contents can change.
