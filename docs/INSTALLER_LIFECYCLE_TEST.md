# Installer lifecycle check on a clean Windows machine

The `packaging/build_lifecycle_fixtures.ps1` script builds a test-only `0.9.0` installer from the current source, alongside the real `1.0.0` candidate. `0.9.0` is a synthetic predecessor for checking installer behavior, not a historical release. The script prints a folder containing both installers, `SHA256.txt`, and synthetic `sample.pdf`, `sample.jpg`, `sample.jpeg`, `sample.png`, `sample.tif`, `sample.tiff`, `sample.bmp`, and `sample.webp`. Never publish the `TEST-ONLY` installer.

Run the following from the project root after building the 1.0.0 installer:

```powershell
.\packaging\build_lifecycle_fixtures.ps1 -InnoCompiler (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
```

Copy the files from the printed `installers` folder to a clean Windows VM or snapshot. Use the same Windows user throughout. Check the SHA-256 values before testing. Record the Windows version, VM snapshot, installer hashes, date, and the results below. A real user document is unnecessary.

| Path | Steps | Expected result | Result |
| --- | --- | --- | --- |
| Fresh install | Run `TEST-ONLY-BlurOutPDF-Setup-0.9.0.exe`. Open each synthetic sample through **Open with**. Check **Installed apps** and the install folder. | One per-user BlurOut PDF entry at version 0.9.0; files under `%LOCALAPPDATA%\Programs\BlurOut PDF`; the app appears as an Open with choice for PDF and all seven raster extensions. | Pending |
| Running app | In the 0.9.0 app, open `sample.pdf`, draw a pending redaction, then start the 1.0.0 installer. Cancel the running-app prompt. Close the app normally without saving the sample. | Setup asks for the app to be closed; cancelling leaves the app and unsaved edit available and does not change the installed version. | Pending |
| Upgrade | In **Settings**, select a language, dark appearance and a redaction style. Close the app. Run `BlurOutPDF-Setup-1.0.0.exe`, then open the app again. | Installation uses the same directory; **Installed apps** has one 1.0.0 entry; preferences remain selected; synthetic documents remain untouched. | Pending |
| Same version | Run `BlurOutPDF-Setup-1.0.0.exe` again. | A localized message says 1.0.0 is installed; no reinstall or registry/file change occurs. | Pending |
| Downgrade | Run `TEST-ONLY-BlurOutPDF-Setup-0.9.0.exe` after 1.0.0 is installed. | A localized message refuses the older version; the 1.0.0 app still launches and preferences remain. | Pending |
| Uninstall | Use **Installed apps → BlurOut PDF → Uninstall**. Check the install folder, **Open with** choices, and synthetic samples. | App files and its Open with registrations are removed; sample files outside the install folder remain. | Pending |

Repeat the same-version and downgrade messages once with each installer language (choose with `/LANG=english` or `/LANG=polish` if Windows chooses automatically). The fixture installers use the same application ID and per-user scope as the release candidate, so these checks exercise the real version gate and upgrade path.

Do not mark Issue 4 complete until all rows have recorded observations from the clean environment. Any failure needs a fix, a new installer build, and a repeat of the affected rows.
