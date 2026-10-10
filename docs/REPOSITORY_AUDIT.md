# Repository publication audit — 2026-10-10

## Scope and evidence

- Reviewed the 30 commits reachable from all local refs, including their changed paths, and scanned 133 unique historical file blobs for personal file paths, email addresses, credential assignments and private-key markers.
- Reviewed the currently tracked file list, `.gitignore`, `.gitattributes`, Windows installer and build scripts, and the CI workflow. The tracked tree contains application source, tests, documentation, configuration, license and application assets only. Generated builds, virtual environments, caches, local PDFs and the local `AGENTS.md` are ignored.
- Checked the README screenshot against `scripts/capture_preview.py`. It shows a PDF generated with invented sample text. The PNG has only DPI metadata; the app icon assets contain no personal metadata.
- The historical content scan found no private document, user-specific absolute path, email address, credential assignment or private key. Test strings such as `SECRET` are synthetic fixtures.
- Commit metadata contains the repository owner's name and email address. The owner confirmed on 2026-10-10 that these may remain public. No history rewrite is needed for this finding.

## Publication boundary

This audit covers local refs and their reachable Git history as of commit `1b96f8a`. Before publication, verify that the remote's refs do not expose additional history and repeat the audit if new files or commits are added. Dependency licensing and installer notices are tracked separately in Issue 2.
