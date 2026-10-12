# Repository publication audit — updated 2026-10-12

## Scope and evidence

- Reviewed the 55 commits reachable from the current `main` branch, including their changed paths, and scanned 247 unique historical file blobs for personal file paths, email addresses, credential assignments and private-key markers.
- Reviewed the currently tracked file list, `.gitignore`, `.gitattributes`, Windows installer and build scripts, and the CI workflow. The tracked tree contains application source, tests, documentation, configuration, license and application assets only. Generated builds, virtual environments, caches, local PDFs and the local `AGENTS.md` are ignored.
- Checked the README screenshot: it shows a PDF with invented sample text. The PNG has only DPI metadata; the app icon assets contain no personal metadata.
- The history scan found no private document, user-specific absolute path, personal email in file contents, real credential assignment or private key. Two email addresses in the Pillow license are FreeType project contact addresses. Matches for `secret`/`password` are synthetic redaction test names and fixtures.
- Commit metadata contains the repository owner's name and email address. The owner confirmed on 2026-10-10 that these may remain public. No history rewrite is needed for this finding.

## Publication boundary

The initial historical content audit covered 30 commits through `1b96f8a`. After publication, this review was extended through public commit `6a1e3be` (39 reachable commits). The intervening commits add the release version and About dialog, licensing notices, installer lifecycle controls, a Qt DLL compatibility fix, and the controlled release build and verifier; their changed files were reviewed. A targeted history scan found `secret=` only in synthetic redaction test/preview data, with no private keys, credential assignments or user-specific absolute paths. The owner confirmed on 2026-10-10 that commit author identity may remain public.

The public repository is [janmadrzyk/blur-out-pdf](https://github.com/janmadrzyk/blur-out-pdf). The current audit was run on 2026-10-12 before publishing version 1.0.1. The Windows workflow passed for commit `824afee` in run [38282940190](https://github.com/janmadrzyk/blur-out-pdf/actions/runs/38282940190) and retained the installer artifact. Dependency licensing and installer notices are tracked separately in Issue 2; release artifact checks are recorded in Issues 5–7.
