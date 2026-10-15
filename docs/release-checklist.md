# Beta release checklist

- [x] The integration pull request is reviewed and merged to `main`.
- [x] Guided CLI onboarding was removed from the beta gate in issue #7; the primary agent integrations use zero-configuration defaults.
- [x] CI passes on macOS, Ubuntu, and Windows for Python 3.9, 3.11, and 3.13.
- [x] `python3 scripts/check_version.py --tag v0.1.0-beta.1` passes.
- [x] `python3 scripts/audit_release.py` reports no private paths, likely secrets, databases, or backups.
- [x] Two clean builds produce identical SHA-256 checksums.
- [x] Upgrade from both bundled v0 fixtures passes and rollback is exercised.
- [x] Claude plugin validates and completes install/disable/enable/uninstall lifecycle.
- [x] Codex plugin validates; marketplace add/install/list/remove/reinstall and bundled-runtime smoke tests pass in a current Codex build; desktop hook trust is confirmed in a new task.
- [x] Release notes include support matrix, migrations, rollback, limitations, feedback, and security links.
- [ ] Maintainer creates and pushes an annotated, signed tag: `git tag -s v0.1.0-beta.1 -m "Mogoj v0.1.0-beta.1"`.
- [ ] GitHub Actions verifies the signed tag, reruns tests, builds artifacts/SBOM/checksums, and creates the prerelease.
- [ ] Downloaded artifact checksum is verified on a clean machine before announcement.
