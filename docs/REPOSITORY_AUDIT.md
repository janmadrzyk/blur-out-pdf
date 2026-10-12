# Repository publication audit — updated 2026-10-12

## Scope and evidence

- Reviewed the 30 commits reachable from all local refs, including their changed paths, and scanned 133 unique historical file blobs for personal file paths, email addresses, credential assignments and private-key markers.
- Reviewed the currently tracked file list, `.gitignore`, `.gitattributes`, Windows installer and build scripts, and the CI workflow. The tracked tree contains application source, tests, documentation, configuration, license and application assets only. Generated builds, virtual environments, caches, local PDFs and the local `AGENTS.md` are ignored.
- Checked the README screenshot: it shows a PDF with invented sample text. The PNG has only DPI metadata; the app icon assets contain no personal metadata.
- The historical content scan found no private document, user-specific absolute path, email address, credential assignment or private key. Test strings such as `SECRET` are synthetic fixtures.
- Commit metadata contains the repository owner's name and email address. The owner confirmed on 2026-10-10 that these may remain public. No history rewrite is needed for this finding.

## Publication boundary

The initial historical content audit covered 30 commits through `1b96f8a`. After publication, this review was extended through public commit `6a1e3be` (39 reachable commits). The intervening commits add the release version and About dialog, licensing notices, installer lifecycle controls, a Qt DLL compatibility fix, and the controlled release build and verifier; their changed files were reviewed. A targeted history scan found `secret=` only in synthetic redaction test/preview data, with no private keys, credential assignments or user-specific absolute paths. The owner confirmed on 2026-10-10 that commit author identity may remain public.

The public repository is [janmadrzyk/blur-out-pdf](https://github.com/janmadrzyk/blur-out-pdf). GitHub Actions run [38152420931](https://github.com/janmadrzyk/blur-out-pdf/actions/runs/38152420931) for `main` at `6a1e3be` completed successfully and retained the Windows installer artifact. No release tag was present in the reviewed local refs. Dependency licensing and installer notices are tracked separately in Issue 2; release artifact checks are recorded in Issue 5.
