# BlurOut PDF 1.0 release issues

This is the editable checklist for preparing the first public release. Work through the issues in order unless a dependency explicitly allows parallel work. Change an issue's checkbox from `[ ]` to `[x]` only after every item in its Definition of Done has been verified. Record the relevant commit, test evidence and date below that issue when closing it. Keep unrelated work in separate issues and commits. All screenshots and test documents used for publication must be synthetic or explicitly approved for that purpose.

## Issue 1 — Audit and prepare the repository

- [x] **Issue 1 complete**

**Depends on:** Nothing.

**Work:**

1. Inspect tracked files, Git history intended for publication, build configuration and ignore rules for private data, obsolete artifacts and generated files. Do not open files outside the project without specific permission.
2. Remove or replace material that should not be published. If history contains private material, plan a safe history rewrite before making the repository public; deleting it from the current tree alone is insufficient.
3. Organize project documentation and add a concise project overview, feature list, supported formats, limitations, development setup and screenshots made from synthetic files.

**Definition of Done:**

- The tracked tree contains only source, tests, assets, configuration, license and documentation needed to build, use or maintain the app.
- No private document, path, credential or personal data remains in the history intended for publication; any required history cleanup has been verified.
- A new contributor can find the setup and build instructions from the README, and a prospective user can understand the features and limitations.
- `git status` is clean after the focused documentation/repository commit.

**Completion record:** 2026-10-10. Commit `54278e1` updates the README and adds the [repository audit](REPOSITORY_AUDIT.md). Evidence: 30 reachable commits and 133 unique historical file blobs reviewed; no private project content found; the owner approved the author identity in commit metadata. The screenshot source and image metadata were checked, local documentation links passed, and `git diff --check` was clean. The checklist closure is recorded in the following commit.

## Issue 2 — Document OCR behavior and third-party licensing

- [x] **Issue 2 complete**

**Depends on:** Issue 1.

**Work:**

1. Document that embedded PDF text search works without OCR, while scanned-page search depends on a locally available OCR engine and compatible language data.
2. Explain automatic language choice, user selection, the bottom status-bar message when OCR data is unavailable, and how a user can supply OCR support independently. Do not bundle or download models in the installer.
3. Audit direct and bundled dependencies, fonts/icons and build tools for licenses, notices and redistribution obligations. Add required notices or attribution to the repository and installer package.

**Definition of Done:**

- README describes the OCR dependency accurately and makes clear that availability may differ between computers; it does not promise OCR on a clean Windows installation.
- The app still reports missing OCR support through the existing status-bar behavior, while embedded-text search and normal viewing remain usable.
- A reviewed dependency/license inventory exists, required notices are present, and the release packaging includes them where required.
- No OCR model file is included in source control or the installer.

**Completion record:** 2026-10-11. Commit `ebbc891` documents OCR behavior, records the dependency/license inventory and adds license texts and notices to the packaging flow. Evidence: four targeted OCR/search checks passed; a synthetic PDF confirmed the missing-OCR status message while embedded-text search stayed available; a fresh local PyInstaller build and `scripts/prepare_bundle.py` produced the expected notice files with no `.traineddata` or Qt Virtual Keyboard files. The installer script recursively includes this prepared bundle. Final candidate installer contents remain an Issue 5 check. The checklist closure is recorded in the following commit.

## Issue 3 — Establish version 1.0.0 in the app and documentation

- [x] **Issue 3 complete**

**Depends on:** Issues 1 and 2.

**Work:**

1. Introduce one authoritative version value and use it in the Python package, application, Windows executable metadata and installer build.
2. Add an About dialog showing BlurOut PDF, version, license and a project link. Translate user-facing text into Polish and English.
3. Prepare `CHANGELOG.md` and release notes for 1.0.0, distinguishing shipped behavior from future ideas.

**Definition of Done:**

- The running app, executable properties, installer and release documents all report `1.0.0` from the same version source or a checked build-time derivation.
- The About dialog is legible in light and dark themes and both UI languages.
- The changelog accurately describes the tested release; no `v1.0.0` tag is created before release-candidate acceptance.
- Relevant automated checks and a manual About-dialog check pass.

**Completion record:** 2026-10-11. Commit `6891c4d` establishes one version source, derives Python package metadata and Windows build versions, adds the bilingual About dialog and drafts release documents. Evidence: Python metadata generated as `blurout_pdf-1.0.0`, a local PyInstaller build reported `FileVersion` and `ProductVersion` 1.0.0, and the installer build scripts pass that value to Inno Setup. The full suite passed (42 passed, 1 skipped); the About dialog was visually inspected in Polish and English with light and dark palettes using Windows rendering. No release tag was created. The final installer itself remains to be built and accepted in Issues 5–6. Checklist closure is recorded in the following commit.

## Issue 4 — Implement installer version lifecycle

- [ ] **Issue 4 complete**

**Depends on:** Issue 3.

**Work:**

1. Keep a stable installer application identity, install directory and per-user/per-machine scope across builds.
2. Define and implement four paths: fresh install, upgrade from an older version, same-version notice with no reinstall, and refusal of an accidental downgrade.
3. Preserve user settings during upgrade; handle a running app safely; keep file association/Open with registration and uninstall behavior working.
4. Localize installer messages in Polish and English where supported by the installer.

**Definition of Done:**

- On a clean Windows test environment, the installer installs the app and Open with entries work for supported formats.
- Installing a newer version upgrades the same app in place, preserves preferences and does not create a duplicate installation.
- Running the same installer twice reports that the version is already installed; running an older installer after an upgrade refuses downgrade without damaging the newer install.
- A running app is handled predictably, and uninstall removes app-owned files/registrations while preserving user documents.
- All four paths have recorded manual test results and the installer script is committed.

**Manual check plan:** [Installer lifecycle on clean Windows](INSTALLER_LIFECYCLE_TEST.md). The owner will record the results from a separate Windows environment before this issue is closed.

**Progress record:** 2026-10-12. The owner reports that upgrading 0.9.0 to 1.0.0 preserved the chosen language, dark appearance and redaction style, kept one app entry in the same directory, and left samples untouched. Re-running the 1.0.0 installer showed the localized already-installed message. A 0.9.0 installation showed the correct About version and project link, and all synthetic samples opened. Cancelling the 1.0.0 installer while 0.9.0 had a pending redaction closed setup while leaving the app and selection intact; closing the app then warned about unsaved changes. The owner also reports uninstalling 1.0.0, though the following setup warned that its install directory already existed; verify remaining files during uninstall testing. Windows Open with integration was not available and is tracked in Issue 8. See [the manual lifecycle results](INSTALLER_LIFECYCLE_TEST.md). Verify same-version state preservation, uninstall cleanup, and downgrade state preservation before closure.

## Issue 5 — Unify and verify release builds

- [ ] **Issue 5 complete**

**Depends on:** Issues 2, 3 and 4.

**Work:**

1. Make local and GitHub CI builds use the same documented commands and pinned or otherwise controlled dependencies.
2. Build the Windows executable and single installer in CI; include license notices and application icon.
3. Run automated tests on synthetic PDF and raster fixtures, and publish build artifacts for release-candidate testing.
4. Generate a SHA-256 checksum for the candidate installer.

**Definition of Done:**

- A clean checkout can follow the README build instructions and produce a working installer.
- CI builds and tests pass from the release candidate commit, and its artifact version matches the app and installer version.
- The built package contains the required notices, icon and supported file integrations, but no OCR models or private fixtures.
- The candidate installer and its checksum are retained together for the acceptance pass.

**Progress record:** 2026-10-12. Commit `6a1e3be` unifies local and CI packaging, controls the Windows dependency versions, verifies the release payload and generates `SHA256.txt`. Local verification passed (48 tests passed, 1 skipped; installer payload and checksum verified). GitHub Actions run [38152420931](https://github.com/janmadrzyk/blur-out-pdf/actions/runs/38152420931) passed on `main` and retained the Windows installer artifact. Keep Issue 5 open until its declared dependency, Issue 4, is complete; then confirm the CI artifact is the candidate used for Issue 6.

## Issue 6 — Accept the release candidate

- [ ] **Issue 6 complete**

**Depends on:** Issue 5.

**Work:**

1. Install the exact candidate artifact in a clean Windows environment and repeat the install, upgrade, same-version, downgrade and uninstall checks.
2. Exercise PDF and raster open/save/export, redaction and reopening results in an independent viewer, multi-tab isolation, search, optional OCR status, rotations, metadata editing, themes and both languages using synthetic fixtures.
3. Check large-file behavior, error dialogs and keyboard access for release-blocking problems. Record known limitations in the README and changelog.
4. Verify the installer checksum and confirm the artifact tested is byte-for-byte the artifact to publish.

**Definition of Done:**

- A written test record identifies the Windows environment, candidate commit, installer filename/checksum, test results and any accepted limitations.
- No release-blocking functional, privacy or installation defect remains; fixes trigger a new build and another test of the changed artifact.
- The README and changelog match observed behavior, including OCR limits and the privacy caveat for blurred covers.
- The candidate is explicitly accepted for publication; its checksum is final.

**Completion record:** _Commit / evidence / date to be added._

## Issue 7 — Publish version 1.0.0 on GitHub

- [ ] **Issue 7 complete**

**Depends on:** Issue 6 and the owner's approval to publish.

**Work:**

1. Confirm the public repository has the audited files, license, README, screenshots and changelog.
2. Tag the accepted commit `v1.0.0` and create a GitHub Release with concise release notes.
3. Attach the exact accepted installer and its SHA-256 checksum, then verify the public download and checksum.

**Definition of Done:**

- The `v1.0.0` tag points to the accepted source commit and the release assets match the tested checksum.
- Public README, license, notices, screenshots and installation instructions render correctly.
- The GitHub Release is accessible and its installer can be downloaded and verified against the published checksum.
- This checkbox is marked complete only after publication succeeds and the release URL is recorded below.

**Progress record:** 2026-10-12. The public source repository is available at [janmadrzyk/blur-out-pdf](https://github.com/janmadrzyk/blur-out-pdf), and the updated repository audit is recorded in `REPOSITORY_AUDIT.md`. No 1.0.0 release has been created. Tagging and release publication wait for Issue 6 acceptance and the owner's release approval.

## Issue 8 — Restore Windows Open with integration

- [ ] **Issue 8 complete**

**Discovered during:** Issue 4 manual installation checks, 2026-10-12.

**Problem:** After installing the test version, BlurOut PDF did not appear in Windows **Open with** for PDFs or supported image files, including **Choose another app**. The files can still be opened from inside the application.

**Work:** Diagnose and fix how the installer registers BlurOut PDF for PDFs and supported raster formats. Keep it available as an option without changing the default viewer, and make sure uninstall removes the registrations.

**Definition of Done:**

- After a fresh install, BlurOut PDF appears under **Open with → Choose another app** for PDF and each supported raster extension.
- Selecting it opens each synthetic sample in BlurOut PDF; existing default applications remain unchanged.
- After uninstall, BlurOut PDF is removed from those **Open with** lists.
- Manual results are recorded on the clean Windows environment.

**Completion record:** _Commit / evidence / date to be added._

## Issue 9 — Show the selection marquee in the file picker

- [ ] **Issue 9 complete**

**Discovered during:** Manual file selection, 2026-10-12.

**Problem:** In the “Open document or image” dialog, dragging to select files applies the rectangular selection, but the selection marquee is not visible under the pointer.

**Work:** Make the dragged selection rectangle visible while selecting one or more files in the dialog.

**Definition of Done:**

- A visible marquee follows the pointer while dragging in the file picker.
- Drag selection still selects the intended files; normal click and multi-select behavior continue to work.
- The behavior is manually checked on Windows.

**Completion record:** _Commit / evidence / date to be added._
