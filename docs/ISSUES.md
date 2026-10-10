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

- [ ] **Issue 2 complete**

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

**Completion record:** _Commit / evidence / date to be added._

## Issue 3 — Establish version 1.0.0 in the app and documentation

- [ ] **Issue 3 complete**

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

**Completion record:** _Commit / evidence / date to be added._

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

**Completion record:** _Commit / evidence / date to be added._

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

**Completion record:** _Commit / evidence / date to be added._

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

**Completion record:** _Release URL / commit / evidence / date to be added._
