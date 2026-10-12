"""Install and uninstall the candidate on an ephemeral GitHub Windows runner.

This deliberately refuses local execution: the probe creates synthetic shared
association values in HKCU and exercises the real installer at its default path.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time
import winreg


PROJECT = Path(__file__).resolve().parents[1]
CLASSES = "Software\\Classes\\"
SUFFIXES = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")
APP_KEYS = ("BlurOutPDF.PDF", "BlurOutPDF.Raster", r"Applications\BlurOutPDF.exe")
SENTINEL = "BlurOutPDF.CI.OtherReader"


def values(path: str) -> dict[str, tuple[object, int]] | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLASSES + path) as key:
            return {
                name: (value, kind)
                for name, value, kind in (
                    winreg.EnumValue(key, index)
                    for index in range(winreg.QueryInfoKey(key)[1])
                )
            }
    except FileNotFoundError:
        return None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_installer(path: Path, log: Path) -> None:
    result = subprocess.run(
        [str(path), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={log}"],
        timeout=300,
        check=False,
    )
    require(result.returncode == 0, f"{path.name} failed with {result.returncode}; see {log}")


def main() -> None:
    require(
        os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Windows",
        "This integration probe may only run on an ephemeral GitHub Actions Windows runner.",
    )
    candidates = list((PROJECT / "dist").glob("BlurOutPDF-Setup-*.exe"))
    require(len(candidates) == 1, "Expected exactly one built installer candidate.")
    install_dir = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "BlurOut PDF"
    require(not install_dir.exists(), f"Refusing to modify an existing installation: {install_dir}")
    for path in APP_KEYS:
        require(values(path) is None, f"Unexpected existing app registration: {path}")
    logs = PROJECT / "build" / "installer-runtime"
    logs.mkdir(parents=True, exist_ok=True)
    fixtures: list[tuple[str, str]] = []
    baseline: dict[str, dict[str, tuple[object, int]]] = {}
    try:
        for suffix in SUFFIXES:
            # Seed a foreign default and Open-with candidate so broad deletion
            # or unintended default-association changes fail this probe.
            for path, name in ((suffix, ""), (suffix + r"\OpenWithProgids", SENTINEL)):
                existing = values(path) or {}
                if name not in existing:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CLASSES + path) as key:
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, SENTINEL if not name else "")
                    fixtures.append((path, name))
                baseline[path] = values(path) or {}
        # Reproduce a leftover empty directory from an earlier uninstall.
        install_dir.mkdir(parents=True)
        uninstaller = install_dir / "unins000.exe"
        try:
            run_installer(candidates[0], logs / "install.log")
            executable = install_dir / "BlurOutPDF.exe"
            require(executable.is_file(), "Installed application executable is missing.")
            command = f'"{executable}" "%1"'
            for path in APP_KEYS:
                actual = values(path + r"\shell\open\command") or {}
                require(actual.get("") == (command, winreg.REG_SZ), f"Incorrect launch command: {path}")
            require(
                (values(APP_KEYS[2]) or {}).get("FriendlyAppName") == ("BlurOut PDF", winreg.REG_SZ),
                "Missing Applications friendly name.",
            )
            supported = values(APP_KEYS[2] + r"\SupportedTypes") or {}
            for suffix in SUFFIXES:
                progid = "BlurOutPDF.PDF" if suffix == ".pdf" else "BlurOutPDF.Raster"
                registered = values(suffix + r"\OpenWithProgids") or {}
                require(registered.get(progid) == ("", winreg.REG_SZ), f"Missing empty REG_SZ: {suffix} / {progid}")
                require(supported.get(suffix) == ("", winreg.REG_SZ), f"Missing Applications SupportedTypes: {suffix}")
            for path, expected in baseline.items():
                actual = values(path)
                require(actual is not None and all(actual.get(k) == v for k, v in expected.items()),
                        f"Installation changed a shared/default association: {path}")
            print("Installed candidate: all eight Open-with registrations and three launch commands passed.")
        finally:
            if uninstaller.is_file():
                run_installer(uninstaller, logs / "uninstall.log")
        # Windows may finish deleting the uninstaller after its process exits.
        deadline = time.monotonic() + 30
        while install_dir.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        require(not install_dir.exists(), f"Uninstall left application files or directory: {install_dir}")
        for path in APP_KEYS:
            require(values(path) is None, f"Uninstall left app registration: {path}")
        for path, expected in baseline.items():
            require(values(path) == expected, f"Uninstall changed shared/default association values: {path}")
        print("Uninstalled candidate: app registrations/files removed; shared/default associations preserved.")
    finally:
        # Remove only synthetic values; never remove shared extension keys.
        for path, name in reversed(fixtures):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLASSES + path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
