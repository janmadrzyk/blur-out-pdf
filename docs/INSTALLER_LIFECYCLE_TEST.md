# Installer lifecycle check on a clean Windows machine

The `packaging/build_lifecycle_fixtures.ps1` script builds test-only `0.9.0` and `1.0.0` installers from the current source, alongside the real candidate identified by `src/blurout_pdf/_version.py` (currently `1.0.1`). These are synthetic predecessors for checking installer behavior, not historical releases or copies of earlier candidate binaries. The script prints a folder containing all three installers, `SHA256.txt`, and synthetic `sample.pdf`, `sample.jpg`, `sample.jpeg`, `sample.png`, `sample.tif`, `sample.tiff`, `sample.bmp`, and `sample.webp`. Never publish the `TEST-ONLY` installers.

The installer lists English first and Polish second in `packaging/windows.iss`. On a first install, it uses Inno Setup's default language detection, which follows the Windows UI language; if that language is unsupported, English is selected as the first listed language. A language selection dialog lets the user override the detected language. Thus Polish Windows selects Polish, while English or unsupported-language Windows selects English on first install. Inno Setup's default `UsePreviousLanguage=yes` setting means later runs may use the language selected during the previous installation. See [Inno Setup's language selection rules](https://jrsoftware.org/ishelp/topic_languagessection.htm) and [UsePreviousLanguage](https://jrsoftware.org/ishelp/topic_setup_usepreviouslanguage.htm).

Run the following from the project root after building the current candidate installer:

```powershell
.\packaging\build_lifecycle_fixtures.ps1 -InnoCompiler (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
```

Copy the files from the printed `installers` folder to a clean Windows VM or snapshot. Use the same Windows user throughout. Check the SHA-256 values before testing. Record the Windows version, VM snapshot, installer hashes, date, and the results below. A real user document is unnecessary.

## Earlier 1.0.0 candidate results

These observations apply to the previous candidate. They do not accept the new 1.0.1 artifact.

| Path | Steps | Expected result | Result |
| --- | --- | --- | --- |
| Fresh install | Run `TEST-ONLY-BlurOutPDF-Setup-0.9.0.exe`. Open each synthetic sample through **Open with**. Check **Installed apps** and the install folder. | One per-user BlurOut PDF entry at version 0.9.0; files under `%LOCALAPPDATA%\Programs\BlurOut PDF`; the app appears as an Open with choice for PDF and all seven raster extensions. | Partially passed — owner reports setup completed after accepting a prompt that the destination folder already existed; About showed version 0.9.0 and the GitHub link, and all samples opened in the app. The app is missing from Windows **Open with → Choose another app** for PDFs and supported images; see Issue 8. Check the installed-app entry and determine during uninstall whether the prior 1.0.0 uninstall left app files or only an empty folder. |
| Running app | In the 0.9.0 app, open `sample.pdf`, draw a pending redaction, then start the 1.0.0 installer. Cancel the running-app prompt. Close the app normally without saving the sample. | Setup asks for the app to be closed; cancelling leaves the app and unsaved edit available and does not change the installed version. | Passed — owner reports setup closed after cancellation, the 0.9.0 app remained active with the pending selection, and the app warned about unsaved changes when closed. Sample was closed without saving (2026-10-12). |
| Upgrade | In **Settings**, select a language, dark appearance and a redaction style. Close the app. Run `BlurOutPDF-Setup-1.0.0.exe`, then open the app again. | Installation uses the same directory; **Installed apps** has one 1.0.0 entry; preferences remain selected; synthetic documents remain untouched. | Passed — owner reports version 1.0.0 opened after the upgrade; language, dark appearance and redaction style persisted; there was one app entry in the same directory and samples remained unchanged (2026-10-12). |
| Same version | Run `BlurOutPDF-Setup-1.0.0.exe` again. | A localized message says 1.0.0 is installed; no reinstall or registry/file change occurs. | Passed — owner reports the already-installed message appeared; afterward the app still reported version 1.0.0, retained its settings, and had one Installed apps entry (2026-10-12). |
| Downgrade | Run `TEST-ONLY-BlurOutPDF-Setup-0.9.0.exe` after 1.0.0 is installed. | A localized message refuses the older version; the 1.0.0 app still launches and preferences remain. | Passed — owner reports the 0.9.0 installer refused to downgrade, **Installed apps** retained one BlurOut PDF entry, and version and preferences remained intact (2026-10-12). |
| Uninstall | Use **Installed apps → BlurOut PDF → Uninstall**. Check the install folder, **Open with** choices, and synthetic samples. | App files and its Open with registrations are removed; sample files outside the install folder remain. | Partially passed — owner reports the BlurOut PDF entry disappeared and the synthetic files remained. `%LOCALAPPDATA%\Programs\BlurOut PDF` still existed but was empty. BlurOut PDF was absent from **Open with** before uninstall, so registration cleanup could not be checked (2026-10-12). |

The same-version and downgrade messages were not repeated interactively in both languages. Source review of `packaging/windows.iss` confirms that both messages have English and Polish translations and that the existing/new versions are passed into the corresponding placeholders. The owner accepted this code-level verification instead of another UI run (2026-10-12). The fixture installers use the same application ID and per-user scope as the release candidate, so these paths otherwise exercise the real version gate and upgrade logic.

Do not mark Issue 4 complete until all rows have recorded observations from the clean environment. Any failure needs a fix, a new installer build, and a repeat of the affected rows.

Owner-reported results above are recorded separately from unverified expectations. The 0.9.0 app launch, About version/link, opening each sample, running-app cancellation, upgrade with preference preservation, the same-version message, and downgrade refusal with preserved version/preferences are confirmed. Uninstall removed the app entry and files but left an empty install directory; Open with cleanup could not be checked because the app was absent from the menu beforehand. Windows Open with integration failed and is tracked in Issue 8. Remaining lifecycle checks still need a result.

## Current 1.0.1 candidate checks

Use the exact CI-built `BlurOutPDF-Setup-1.0.1.exe` and verify its checksum before running these checks. Record the candidate commit, CI run, hash and clean Windows environment with the results. Test-only 1.0.0 fixtures exercise the version gate; also check upgrade from an actual earlier 1.0.0 candidate installation when one is available.

| Path | Steps and expected result | Result |
| --- | --- | --- |
| Fresh install and Open with | Install 1.0.1 on a clean snapshot. Confirm one Installed apps entry and About version 1.0.1. Open each synthetic PDF/raster sample through **Open with → Choose another app → BlurOut PDF**; existing default viewers remain selected. | Pending. |
| Running app | Open a synthetic sample with a pending redaction in the predecessor app. Start 1.0.1 setup and cancel the close-app prompt; the app, version and pending selection remain available. | Pending. |
| Upgrade from 0.9.0 and 1.0.0 | On separate snapshots, install each predecessor, choose language, appearance and cover style, then install 1.0.1. Confirm one app entry, About version 1.0.1, preserved settings, untouched samples and working Open with entries. | Pending. |
| Same version | Run 1.0.1 setup again. Confirm the already-installed message, preserved settings and one app entry. | Pending. |
| Downgrade | Run each TEST-ONLY predecessor installer after 1.0.1 is installed. Confirm refusal while version 1.0.1 and settings remain intact. | Pending. |
| File picker selection | In the 1.0.1 app, choose **Open**, drag across synthetic files and confirm a visible selection marquee, the intended selection, and normal click/multi-select behavior. | Pending. |
| Uninstall | Uninstall 1.0.1. Confirm the app entry and app-owned files/registrations disappear, including all Open with entries. Confirm external samples remain. Check whether the install directory is removed or remains empty and record the outcome. | Pending. |

Complete these observations and the application acceptance checks in Issue 6 before tagging or publishing the candidate.
