# Third-party notices

BlurOut PDF is licensed under AGPL-3.0-only. See the adjacent `LICENSE` file. The corresponding application source is distributed in the project repository. This package includes software from the following projects:

| Component | License and notice |
| --- | --- |
| CPython | Copyright Python Software Foundation and prior contributors. The Python license stack is in `licenses/Python-LICENSE.txt`; see [Python licensing](https://docs.python.org/3.12/license.html). |
| PyMuPDF and MuPDF | Copyright Artifex Software, Inc. and contributors. Used under AGPL-3.0; see the adjacent `LICENSE` and [PyMuPDF license information](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright). |
| PySide6, Shiboken6 and Qt | Copyright The Qt Company Ltd. and contributors. Used under LGPL-3.0 for the modules in this package. `licenses/LGPL-3.0.txt` and `licenses/GPL-3.0.txt` contain the license terms. See [Qt for Python licensing](https://doc.qt.io/qtforpython-6/) and [Qt third-party attributions](https://doc.qt.io/qt-6.11/licenses-used-in-qt.html) for components included in Qt. Qt libraries are dynamic files in the `_internal/PySide6` directory and may be replaced with compatible modified builds. |
| Pillow and bundled image libraries | Copyright Jeffrey A. Clark, Secret Labs AB, Fredrik Lundh and contributors. `licenses/Pillow-LICENSE.txt` contains Pillow's MIT-CMU terms and its bundled third-party notices. |

The executable contains the PyInstaller bootloader. [PyInstaller's bootloader exception](https://pyinstaller.org/en/stable/license.html) permits distributing applications under their own compatible licenses and does not require a separate PyInstaller notice. The Inno Setup compiler is a build tool; it is not installed as an application component.

No Tesseract language models are included. OCR may use compatible data installed independently on the user's computer.
